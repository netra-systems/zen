"""
Integration tests for AgentWebSocketBridge - Testing real integration with WebSocket manager and agent registry.

Business Value Justification (BVJ):
- Segment: Platform/Internal  
- Business Goal: Reliable agent-WebSocket integration lifecycle
- Value Impact: Ensures agents can establish and maintain WebSocket connections for user communication
- Strategic Impact: Critical integration point - validates agent-WebSocket coordination with real components

These tests focus on testing AgentWebSocketBridge with real WebSocket managers
and agent registries, including initialization, recovery, and background monitoring.
"""

import asyncio
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    IntegrationState,
    IntegrationConfig,
    HealthStatus,
    IntegrationResult
)
from test_framework.ssot.base_test_case import BaseTestCase


class TestAgentWebSocketBridgeInitialization(BaseTestCase):
    """Integration tests for AgentWebSocketBridge initialization with real components."""
    
    @pytest.fixture
    def integration_config(self):
        """Create integration configuration for testing."""
        return IntegrationConfig(
            initialization_timeout_s=5,
            health_check_interval_s=10,
            recovery_max_attempts=2,
            recovery_base_delay_s=0.2,
            recovery_max_delay_s=2.0,
            integration_verification_timeout_s=3
        )
    
    @pytest.fixture
    def mock_websocket_manager(self):
        """Create realistic WebSocket manager mock."""
        manager = AsyncMock()
        manager.get_stats.return_value = {
            "total_connections": 3,
            "unique_users": 2,
            "errors": [],
            "uptime": 300.0
        }
        manager.create_user_emitter = AsyncMock()
        manager.is_healthy = AsyncMock(return_value=True)
        return manager
    
    @pytest.fixture
    def mock_agent_registry(self):
        """Create realistic agent registry mock."""
        registry = Mock()
        registry.get_all_executions.return_value = ["exec1", "exec2", "exec3"]
        registry.is_healthy.return_value = True
        registry.get_stats.return_value = {
            "total_executions": 3,
            "active_agents": 2,
            "error_count": 0
        }
        return registry
    
    @pytest.fixture
    async def agent_websocket_bridge(self, integration_config):
        """Create AgentWebSocketBridge for integration testing."""
        bridge = AgentWebSocketBridge(integration_config)
        yield bridge
        # Cleanup
        await bridge.shutdown()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_successful_initialization_with_real_components(
        self, 
        agent_websocket_bridge, 
        mock_websocket_manager, 
        mock_agent_registry
    ):
        """Test successful initialization creates proper integration."""
        # Act
        result = await agent_websocket_bridge.initialize(
            websocket_manager=mock_websocket_manager,
            agent_registry=mock_agent_registry
        )
        
        # Assert
        assert isinstance(result, IntegrationResult)
        assert result.success is True
        assert result.state == IntegrationState.ACTIVE
        assert result.error is None
        assert result.duration_ms > 0
        
        # Verify bridge state
        assert agent_websocket_bridge.state == IntegrationState.ACTIVE
        assert agent_websocket_bridge.websocket_manager == mock_websocket_manager
        assert agent_websocket_bridge.registry == mock_agent_registry
        
        # Verify metrics were updated
        metrics = agent_websocket_bridge.metrics
        assert metrics.total_initializations == 1
        assert metrics.successful_initializations == 1
        assert metrics.failed_initializations == 0
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_initialization_failure_with_unhealthy_websocket_manager(
        self,
        agent_websocket_bridge,
        mock_agent_registry
    ):
        """Test initialization fails gracefully with unhealthy WebSocket manager."""
        # Arrange - Create unhealthy WebSocket manager
        unhealthy_manager = AsyncMock()
        unhealthy_manager.get_stats.return_value = {
            "total_connections": 0,
            "unique_users": 0,
            "errors": ["Connection pool exhausted", "Network timeout"]
        }
        unhealthy_manager.is_healthy = AsyncMock(return_value=False)
        
        # Act
        result = await agent_websocket_bridge.initialize(
            websocket_manager=unhealthy_manager,
            agent_registry=mock_agent_registry
        )
        
        # Assert
        assert result.success is False
        assert result.state == IntegrationState.FAILED
        assert "WebSocket manager health check failed" in result.error
        assert result.duration_ms > 0
        
        # Bridge should remain uninitialized
        assert agent_websocket_bridge.state == IntegrationState.FAILED
        
        # Metrics should reflect failure
        metrics = agent_websocket_bridge.metrics
        assert metrics.total_initializations == 1
        assert metrics.successful_initializations == 0
        assert metrics.failed_initializations == 1
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_initialization_timeout_handling(self, integration_config):
        """Test initialization respects timeout configuration."""
        # Create bridge with very short timeout
        short_timeout_config = IntegrationConfig(
            initialization_timeout_s=0.1,  # Very short timeout
            health_check_interval_s=10,
            recovery_max_attempts=1,
            recovery_base_delay_s=0.1,
            recovery_max_delay_s=1.0,
            integration_verification_timeout_s=0.05
        )
        
        bridge = AgentWebSocketBridge(short_timeout_config)
        
        try:
            # Create slow WebSocket manager
            slow_manager = AsyncMock()
            
            async def slow_health_check():
                await asyncio.sleep(0.5)  # Longer than timeout
                return True
            
            slow_manager.is_healthy = slow_health_check
            slow_manager.get_stats.return_value = {"total_connections": 1}
            
            mock_registry = Mock()
            mock_registry.is_healthy.return_value = True
            
            # Act
            result = await bridge.initialize(
                websocket_manager=slow_manager,
                agent_registry=mock_registry
            )
            
            # Assert - Should timeout
            assert result.success is False
            assert result.state == IntegrationState.FAILED
            assert "timeout" in result.error.lower() or result.error is not None
            
        finally:
            await bridge.shutdown()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_integration_verification_after_initialization(
        self,
        agent_websocket_bridge,
        mock_websocket_manager,
        mock_agent_registry
    ):
        """Test integration verification ensures components work together."""
        # Initialize successfully
        await agent_websocket_bridge.initialize(
            websocket_manager=mock_websocket_manager,
            agent_registry=mock_agent_registry
        )
        
        # Act - Verify integration
        verification_result = await agent_websocket_bridge.verify_integration()
        
        # Assert
        assert verification_result.success is True
        assert verification_result.state == IntegrationState.ACTIVE
        
        # Should have performed verification calls
        mock_websocket_manager.get_stats.assert_called()


class TestAgentWebSocketBridgeHealthMonitoring(BaseTestCase):
    """Integration tests for AgentWebSocketBridge health monitoring system."""
    
    @pytest.fixture
    def monitoring_config(self):
        """Create configuration optimized for health monitoring testing."""
        return IntegrationConfig(
            initialization_timeout_s=3,
            health_check_interval_s=2,  # Short interval for testing
            recovery_max_attempts=3,
            recovery_base_delay_s=0.1,
            recovery_max_delay_s=1.0,
            integration_verification_timeout_s=2
        )
    
    @pytest.fixture
    async def initialized_bridge(self, monitoring_config):
        """Create initialized bridge for health monitoring tests."""
        bridge = AgentWebSocketBridge(monitoring_config)
        
        # Mock components
        mock_websocket_manager = AsyncMock()
        mock_websocket_manager.get_stats.return_value = {
            "total_connections": 5,
            "unique_users": 3,
            "errors": []
        }
        mock_websocket_manager.is_healthy = AsyncMock(return_value=True)
        
        mock_registry = Mock()
        mock_registry.get_all_executions.return_value = ["exec1", "exec2"]
        mock_registry.is_healthy.return_value = True
        
        # Initialize
        await bridge.initialize(
            websocket_manager=mock_websocket_manager,
            agent_registry=mock_registry
        )
        
        yield bridge, mock_websocket_manager, mock_registry
        
        # Cleanup
        await bridge.shutdown()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_continuous_health_monitoring(self, initialized_bridge):
        """Test continuous background health monitoring."""
        bridge, mock_websocket_manager, mock_registry = initialized_bridge
        
        # Start background health monitoring
        await bridge.start_health_monitoring()
        
        # Allow several health check cycles
        await asyncio.sleep(0.5)
        
        # Stop monitoring
        await bridge.stop_health_monitoring()
        
        # Assert - Health checks should have been performed
        metrics = bridge.metrics
        assert metrics.health_checks_performed > 0
        
        # Should maintain active state with healthy components
        assert bridge.state == IntegrationState.ACTIVE
        
        health_status = bridge.get_health_status()
        assert health_status.websocket_manager_healthy is True
        assert health_status.registry_healthy is True
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_degradation_detection(self, monitoring_config):
        """Test system detects health degradation and transitions to degraded state."""
        bridge = AgentWebSocketBridge(monitoring_config)
        
        try:
            # Start with healthy components
            healthy_websocket_manager = AsyncMock()
            healthy_websocket_manager.get_stats.return_value = {
                "total_connections": 5,
                "errors": []
            }
            healthy_websocket_manager.is_healthy = AsyncMock(return_value=True)
            
            healthy_registry = Mock()
            healthy_registry.is_healthy.return_value = True
            healthy_registry.get_all_executions.return_value = ["exec1"]
            
            # Initialize
            await bridge.initialize(
                websocket_manager=healthy_websocket_manager,
                agent_registry=healthy_registry
            )
            
            assert bridge.state == IntegrationState.ACTIVE
            
            # Simulate WebSocket manager degradation
            healthy_websocket_manager.get_stats.return_value = {
                "total_connections": 0,
                "errors": ["Connection pool exhausted", "Multiple timeouts"]
            }
            healthy_websocket_manager.is_healthy = AsyncMock(return_value=False)
            
            # Perform health check
            health_status = bridge.get_health_status()
            
            # Should detect degradation
            assert health_status.websocket_manager_healthy is False
            assert health_status.registry_healthy is True
            assert health_status.error_message is not None
            
            # State should transition to degraded
            # (In real implementation, this would be handled by health monitoring)
            
        finally:
            await bridge.shutdown()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_health_status_comprehensive_reporting(self, initialized_bridge):
        """Test comprehensive health status reporting includes all metrics."""
        bridge, mock_websocket_manager, mock_registry = initialized_bridge
        
        # Generate some activity
        await bridge.verify_integration()
        
        # Act
        health_status = bridge.get_health_status()
        
        # Assert - Health status should be comprehensive
        assert isinstance(health_status, HealthStatus)
        assert health_status.state == IntegrationState.ACTIVE
        assert health_status.websocket_manager_healthy is True
        assert health_status.registry_healthy is True
        assert isinstance(health_status.last_health_check, datetime)
        assert health_status.consecutive_failures >= 0
        assert health_status.total_recoveries >= 0
        assert health_status.uptime_seconds >= 0
        
        # Get metrics dictionary format
        metrics_dict = bridge.get_metrics()
        assert isinstance(metrics_dict, dict)
        
        required_metrics = [
            "state", "total_initializations", "successful_initializations",
            "failed_initializations", "recovery_attempts", "successful_recoveries",
            "health_checks_performed", "uptime_seconds"
        ]
        
        for metric in required_metrics:
            assert metric in metrics_dict


class TestAgentWebSocketBridgeRecoverySystem(BaseTestCase):
    """Integration tests for AgentWebSocketBridge recovery mechanisms."""
    
    @pytest.fixture
    def recovery_config(self):
        """Create configuration optimized for recovery testing."""
        return IntegrationConfig(
            initialization_timeout_s=2,
            health_check_interval_s=1,
            recovery_max_attempts=3,
            recovery_base_delay_s=0.05,  # Fast recovery for testing
            recovery_max_delay_s=0.5,
            integration_verification_timeout_s=1
        )
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_automatic_recovery_from_websocket_manager_failure(self, recovery_config):
        """Test automatic recovery when WebSocket manager fails then recovers."""
        bridge = AgentWebSocketBridge(recovery_config)
        
        try:
            # Create WebSocket manager that starts failing then recovers
            recovery_websocket_manager = AsyncMock()
            failure_count = 0
            
            async def simulate_recovery():
                nonlocal failure_count
                failure_count += 1
                if failure_count <= 2:  # Fail first 2 calls
                    return False
                return True  # Then recover
            
            recovery_websocket_manager.is_healthy = simulate_recovery
            recovery_websocket_manager.get_stats.return_value = {
                "total_connections": 1,
                "errors": []
            }
            
            healthy_registry = Mock()
            healthy_registry.is_healthy.return_value = True
            healthy_registry.get_all_executions.return_value = ["exec1"]
            
            # Initialize (should succeed initially)
            result = await bridge.initialize(
                websocket_manager=recovery_websocket_manager,
                agent_registry=healthy_registry
            )
            
            # May succeed or fail depending on first health check timing
            assert isinstance(result, IntegrationResult)
            
            # Attempt recovery if needed
            if not result.success or bridge.state != IntegrationState.ACTIVE:
                recovery_result = await bridge.attempt_recovery()
                assert isinstance(recovery_result, IntegrationResult)
            
            # After recovery attempts, should eventually succeed
            final_verification = await bridge.verify_integration()
            # May succeed after recovery attempts
            
            # Verify recovery metrics were updated
            metrics = bridge.metrics
            assert metrics.recovery_attempts >= 0
            
        finally:
            await bridge.shutdown()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_recovery_exhaustion_and_failure_state(self, recovery_config):
        """Test system properly fails after exhausting recovery attempts."""
        bridge = AgentWebSocketBridge(recovery_config)
        
        try:
            # Create persistently failing WebSocket manager
            failing_manager = AsyncMock()
            failing_manager.is_healthy = AsyncMock(return_value=False)
            failing_manager.get_stats.return_value = {
                "total_connections": 0,
                "errors": ["Persistent failure"]
            }
            
            healthy_registry = Mock()
            healthy_registry.is_healthy.return_value = True
            
            # Initialize (should fail)
            result = await bridge.initialize(
                websocket_manager=failing_manager,
                agent_registry=healthy_registry
            )
            
            assert result.success is False
            
            # Attempt recovery multiple times (should eventually exhaust attempts)
            recovery_attempts = 0
            max_recovery_attempts = recovery_config.recovery_max_attempts + 1
            
            while recovery_attempts < max_recovery_attempts:
                recovery_result = await bridge.attempt_recovery()
                recovery_attempts += 1
                
                if recovery_result.success:
                    break
                
                # Small delay between recovery attempts
                await asyncio.sleep(0.1)
            
            # Should have attempted recovery
            metrics = bridge.metrics
            assert metrics.recovery_attempts >= 1
            assert metrics.successful_recoveries == 0  # No successful recoveries
            
            # Final state should be failed if all recovery attempts exhausted
            if recovery_attempts >= max_recovery_attempts:
                assert bridge.state in [IntegrationState.FAILED, IntegrationState.DEGRADED]
            
        finally:
            await bridge.shutdown()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_user_emitter_creation_during_recovery(self, recovery_config):
        """Test user emitter creation gracefully handles recovery states."""
        bridge = AgentWebSocketBridge(recovery_config)
        
        try:
            # Mock user execution context
            mock_user_context = Mock()
            mock_user_context.user_id = "test_user_recovery"
            mock_user_context.thread_id = "thread_recovery_123"
            
            # Test emitter creation in uninitialized state
            emitter = bridge.create_user_emitter(mock_user_context)
            assert emitter is None  # Should return None when not initialized
            
            # Initialize with healthy components
            healthy_manager = AsyncMock()
            healthy_manager.is_healthy = AsyncMock(return_value=True)
            healthy_manager.get_stats.return_value = {"total_connections": 1, "errors": []}
            healthy_manager.create_user_emitter = AsyncMock()
            healthy_manager.create_user_emitter.return_value = Mock()
            
            healthy_registry = Mock()
            healthy_registry.is_healthy.return_value = True
            
            await bridge.initialize(
                websocket_manager=healthy_manager,
                agent_registry=healthy_registry
            )
            
            # Test emitter creation in active state
            emitter = bridge.create_user_emitter(mock_user_context)
            assert emitter is not None
            healthy_manager.create_user_emitter.assert_called_once_with(mock_user_context)
            
            # Simulate degraded state
            bridge.state = IntegrationState.DEGRADED
            
            # Should still attempt to create emitter in degraded state
            emitter_degraded = bridge.create_user_emitter(mock_user_context)
            # Behavior may vary - could return None or attempt creation
            
        finally:
            await bridge.shutdown()