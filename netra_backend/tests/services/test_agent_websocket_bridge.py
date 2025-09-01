"""
Comprehensive tests for AgentWebSocketBridge - SSOT for WebSocket-Agent integration.

Tests cover:
- Unit tests for bridge functionality
- Integration lifecycle management  
- Idempotent initialization
- Health monitoring and recovery
- Clear boundary separation
- Mission-critical WebSocket event delivery
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone
import uuid

from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    get_agent_websocket_bridge,
    IntegrationState,
    IntegrationResult,
    HealthStatus,
    IntegrationConfig,
    IntegrationMetrics
)


class TestAgentWebSocketBridgeUnit:
    """Unit tests for AgentWebSocketBridge core functionality."""

    @pytest.fixture
    async def bridge(self):
        """Create fresh bridge instance for each test."""
        # Reset singleton for clean tests
        AgentWebSocketBridge._instance = None
        bridge = AgentWebSocketBridge()
        yield bridge
        await bridge.shutdown()

    @pytest.fixture
    def mock_websocket_manager(self):
        """Mock WebSocket manager."""
        manager = AsyncMock()
        manager.send_message = AsyncMock(return_value=True)
        manager.send_error = AsyncMock(return_value=True)
        manager.send_to_thread = AsyncMock(return_value=True)
        return manager

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock WebSocket agent orchestrator."""
        orchestrator = AsyncMock()
        orchestrator.set_websocket_manager = AsyncMock()
        orchestrator.setup_agent_websocket_integration = AsyncMock()
        orchestrator.get_metrics = AsyncMock(return_value={"active_contexts": 0})
        orchestrator.shutdown = AsyncMock()
        return orchestrator

    @pytest.fixture
    def mock_supervisor(self):
        """Mock supervisor agent."""
        supervisor = Mock()
        supervisor.registry = Mock()
        supervisor.registry.websocket_manager = None
        supervisor.registry.set_websocket_manager = Mock()
        return supervisor

    def test_singleton_pattern(self):
        """Test bridge follows singleton pattern correctly."""
        # Reset singleton
        AgentWebSocketBridge._instance = None
        
        bridge1 = AgentWebSocketBridge()
        bridge2 = AgentWebSocketBridge()
        
        assert bridge1 is bridge2
        assert AgentWebSocketBridge._instance is bridge1

    def test_initial_state(self, bridge):
        """Test bridge initializes with correct default state."""
        assert bridge.state == IntegrationState.UNINITIALIZED
        assert bridge._websocket_manager is None
        assert bridge._orchestrator is None
        assert bridge._supervisor is None
        assert bridge._registry is None
        assert not bridge._shutdown

    def test_configuration_defaults(self, bridge):
        """Test bridge uses correct default configuration."""
        config = bridge.config
        
        assert config.initialization_timeout_s == 30
        assert config.health_check_interval_s == 60
        assert config.recovery_max_attempts == 3
        assert config.recovery_base_delay_s == 1.0
        assert config.recovery_max_delay_s == 30.0

    def test_metrics_initialization(self, bridge):
        """Test metrics are initialized correctly."""
        metrics = bridge.metrics
        
        assert metrics.total_initializations == 0
        assert metrics.successful_initializations == 0
        assert metrics.failed_initializations == 0
        assert metrics.recovery_attempts == 0
        assert metrics.successful_recoveries == 0
        assert isinstance(metrics.current_uptime_start, datetime)


class TestAgentWebSocketBridgeIntegration:
    """Integration tests for bridge lifecycle management."""

    @pytest.fixture
    async def bridge(self):
        """Create fresh bridge instance for each test."""
        AgentWebSocketBridge._instance = None
        bridge = AgentWebSocketBridge()
        yield bridge
        await bridge.shutdown()

    @pytest.fixture
    def integration_mocks(self):
        """Complete set of integration mocks."""
        return {
            'websocket_manager': AsyncMock(),
            'orchestrator': AsyncMock(),
            'supervisor': Mock(),
            'registry': Mock()
        }

    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_agent_orchestrator')
    async def test_successful_integration(self, mock_get_orchestrator, mock_get_manager, bridge, integration_mocks):
        """Test successful integration from uninitialized to active."""
        # Setup mocks
        mock_get_manager.return_value = integration_mocks['websocket_manager']
        mock_get_orchestrator.return_value = integration_mocks['orchestrator']
        integration_mocks['orchestrator'].get_metrics.return_value = {"active_contexts": 0}

        # Perform integration
        result = await bridge.ensure_integration(
            supervisor=integration_mocks['supervisor'],
            registry=integration_mocks['registry']
        )

        # Verify success
        assert result.success
        assert result.state == IntegrationState.ACTIVE
        assert result.duration_ms > 0
        assert bridge.state == IntegrationState.ACTIVE
        assert bridge._websocket_manager is integration_mocks['websocket_manager']
        assert bridge._orchestrator is integration_mocks['orchestrator']

        # Verify metrics updated
        assert bridge.metrics.total_initializations == 1
        assert bridge.metrics.successful_initializations == 1
        assert bridge.metrics.failed_initializations == 0

        # Verify orchestrator was configured
        integration_mocks['orchestrator'].set_websocket_manager.assert_called_once()
        integration_mocks['orchestrator'].setup_agent_websocket_integration.assert_called_once()

    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_agent_orchestrator')
    async def test_idempotent_initialization(self, mock_get_orchestrator, mock_get_manager, bridge, integration_mocks):
        """Test integration is idempotent - can be called multiple times safely."""
        # Setup mocks
        mock_get_manager.return_value = integration_mocks['websocket_manager']
        mock_get_orchestrator.return_value = integration_mocks['orchestrator']
        integration_mocks['orchestrator'].get_metrics.return_value = {"active_contexts": 0}

        # First integration
        result1 = await bridge.ensure_integration(
            supervisor=integration_mocks['supervisor'],
            registry=integration_mocks['registry']
        )

        # Second integration (should be no-op)
        result2 = await bridge.ensure_integration(
            supervisor=integration_mocks['supervisor'],
            registry=integration_mocks['registry']
        )

        # Both should succeed
        assert result1.success
        assert result2.success
        assert result1.state == IntegrationState.ACTIVE
        assert result2.state == IntegrationState.ACTIVE

        # Metrics should show only one initialization
        assert bridge.metrics.total_initializations == 1
        assert bridge.metrics.successful_initializations == 1

        # Second call should have minimal duration (quick path)
        assert result2.duration_ms < result1.duration_ms

    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_agent_orchestrator')
    async def test_integration_failure_handling(self, mock_get_orchestrator, mock_get_manager, bridge):
        """Test integration handles failures gracefully."""
        # Setup failure scenario
        mock_get_manager.side_effect = RuntimeError("WebSocket manager unavailable")

        # Attempt integration
        result = await bridge.ensure_integration()

        # Verify failure handling
        assert not result.success
        assert result.state == IntegrationState.FAILED
        assert "WebSocket manager initialization failed" in result.error
        assert bridge.state == IntegrationState.FAILED

        # Verify metrics updated
        assert bridge.metrics.total_initializations == 1
        assert bridge.metrics.successful_initializations == 0
        assert bridge.metrics.failed_initializations == 1

    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_agent_orchestrator')
    async def test_force_reinit_option(self, mock_get_orchestrator, mock_get_manager, bridge, integration_mocks):
        """Test force_reinit parameter forces re-initialization."""
        # Setup mocks
        mock_get_manager.return_value = integration_mocks['websocket_manager']
        mock_get_orchestrator.return_value = integration_mocks['orchestrator']
        integration_mocks['orchestrator'].get_metrics.return_value = {"active_contexts": 0}

        # First integration
        await bridge.ensure_integration()
        first_total = bridge.metrics.total_initializations

        # Second integration with force_reinit=True
        result = await bridge.ensure_integration(force_reinit=True)

        # Should force re-initialization
        assert result.success
        assert bridge.metrics.total_initializations == first_total + 1


class TestAgentWebSocketBridgeHealth:
    """Tests for health monitoring and recovery functionality."""

    @pytest.fixture
    async def bridge(self):
        """Create fresh bridge instance for each test."""
        AgentWebSocketBridge._instance = None
        bridge = AgentWebSocketBridge()
        yield bridge
        await bridge.shutdown()

    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_agent_orchestrator')
    async def test_health_check_active_state(self, mock_get_orchestrator, mock_get_manager, bridge):
        """Test health check for active integration."""
        # Setup active integration
        websocket_manager = AsyncMock()
        orchestrator = AsyncMock()
        orchestrator.get_metrics.return_value = {"active_contexts": 0}
        
        mock_get_manager.return_value = websocket_manager
        mock_get_orchestrator.return_value = orchestrator

        # Initialize successfully
        await bridge.ensure_integration()

        # Perform health check
        health = await bridge.health_check()

        # Verify healthy state
        assert health.state == IntegrationState.ACTIVE
        assert health.websocket_manager_healthy
        assert health.orchestrator_healthy
        assert health.consecutive_failures == 0
        assert health.is_healthy

    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_agent_orchestrator')
    async def test_health_check_degraded_state(self, mock_get_orchestrator, mock_get_manager, bridge):
        """Test health check detects degraded state."""
        # Setup integration with failing orchestrator
        websocket_manager = AsyncMock()
        orchestrator = AsyncMock()
        orchestrator.get_metrics.side_effect = RuntimeError("Orchestrator failure")
        
        mock_get_manager.return_value = websocket_manager
        mock_get_orchestrator.return_value = orchestrator

        # Initialize successfully first
        orchestrator.get_metrics.side_effect = None
        orchestrator.get_metrics.return_value = {"active_contexts": 0}
        await bridge.ensure_integration()

        # Now make orchestrator fail
        orchestrator.get_metrics.side_effect = RuntimeError("Orchestrator failure")

        # Perform health check
        health = await bridge.health_check()

        # Verify degraded state
        assert health.state == IntegrationState.DEGRADED
        assert health.websocket_manager_healthy
        assert not health.orchestrator_healthy
        assert health.consecutive_failures == 1

    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_agent_orchestrator')
    async def test_recovery_mechanism(self, mock_get_orchestrator, mock_get_manager, bridge):
        """Test automatic recovery from failed state."""
        # Setup initially failing integration
        mock_get_manager.side_effect = [
            RuntimeError("Initial failure"),  # First call fails
            AsyncMock()  # Second call succeeds
        ]
        orchestrator = AsyncMock()
        orchestrator.get_metrics.return_value = {"active_contexts": 0}
        mock_get_orchestrator.return_value = orchestrator

        # Initial integration should fail
        result1 = await bridge.ensure_integration()
        assert not result1.success
        assert bridge.state == IntegrationState.FAILED

        # Recovery should succeed
        result2 = await bridge.recover_integration()
        assert result2.success
        assert result2.recovery_attempted
        assert bridge.state == IntegrationState.ACTIVE

        # Verify recovery metrics
        assert bridge.metrics.recovery_attempts == 1
        assert bridge.metrics.successful_recoveries == 1


class TestAgentWebSocketBridgeBoundaries:
    """Tests for clear boundary separation between WebSocket/Agent/Bridge."""

    @pytest.fixture
    async def bridge(self):
        """Create fresh bridge instance for each test."""
        AgentWebSocketBridge._instance = None
        bridge = AgentWebSocketBridge()
        yield bridge
        await bridge.shutdown()

    def test_bridge_doesnt_mix_concerns(self, bridge):
        """Test bridge doesn't mix WebSocket and Agent concerns."""
        # Bridge should only have coordination methods
        bridge_methods = [method for method in dir(bridge) if not method.startswith('_')]
        
        # Should NOT have agent-specific methods
        agent_methods = ['run', 'execute', 'process_message', 'handle_user_input']
        for agent_method in agent_methods:
            assert agent_method not in bridge_methods, f"Bridge should not have agent method: {agent_method}"

        # Should NOT have websocket-specific methods
        websocket_methods = ['send_message', 'handle_connection', 'broadcast']
        for ws_method in websocket_methods:
            assert ws_method not in bridge_methods, f"Bridge should not have websocket method: {ws_method}"

        # Should ONLY have coordination methods
        coordination_methods = [
            'ensure_integration', 'health_check', 'recover_integration', 
            'get_status', 'shutdown', 'get_metrics'
        ]
        for coord_method in coordination_methods:
            assert coord_method in bridge_methods, f"Bridge should have coordination method: {coord_method}"

    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_agent_orchestrator')
    async def test_dependencies_not_leaked(self, mock_get_orchestrator, mock_get_manager, bridge):
        """Test bridge doesn't leak internal dependencies."""
        # Setup integration
        websocket_manager = AsyncMock()
        orchestrator = AsyncMock()
        orchestrator.get_metrics.return_value = {"active_contexts": 0}
        
        mock_get_manager.return_value = websocket_manager
        mock_get_orchestrator.return_value = orchestrator

        # Initialize
        await bridge.ensure_integration()

        # Get status should provide dependency info without leaking instances
        status = await bridge.get_status()
        
        # Should have availability info
        assert "dependencies" in status
        assert "websocket_manager_available" in status["dependencies"]
        assert "orchestrator_available" in status["dependencies"]
        
        # Should NOT leak actual instances
        assert websocket_manager not in str(status)
        assert orchestrator not in str(status)

    async def test_clean_separation_in_status(self, bridge):
        """Test status reporting maintains clean separation."""
        status = await bridge.get_status()
        
        # Should have clear sections
        required_sections = ["state", "health", "metrics", "config", "dependencies"]
        for section in required_sections:
            assert section in status, f"Status should have section: {section}"

        # Health section should be WebSocket-focused
        health = status["health"]
        assert "websocket_manager_healthy" in health
        assert "orchestrator_healthy" in health

        # Metrics section should be integration-focused
        metrics = status["metrics"]
        assert "total_initializations" in metrics
        assert "successful_recoveries" in metrics


class TestAgentWebSocketBridgeAsync:
    """Tests for async lifecycle and resource management."""

    @pytest.fixture
    async def bridge(self):
        """Create fresh bridge instance for each test."""
        AgentWebSocketBridge._instance = None
        bridge = AgentWebSocketBridge()
        yield bridge
        await bridge.shutdown()

    async def test_singleton_factory_function(self):
        """Test get_agent_websocket_bridge factory function."""
        # Reset singleton
        AgentWebSocketBridge._instance = None
        
        bridge1 = await get_agent_websocket_bridge()
        bridge2 = await get_agent_websocket_bridge()
        
        assert bridge1 is bridge2
        assert isinstance(bridge1, AgentWebSocketBridge)
        
        await bridge1.shutdown()

    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_agent_orchestrator')
    async def test_concurrent_initialization(self, mock_get_orchestrator, mock_get_manager, bridge):
        """Test bridge handles concurrent initialization correctly."""
        # Setup mocks
        websocket_manager = AsyncMock()
        orchestrator = AsyncMock()
        orchestrator.get_metrics.return_value = {"active_contexts": 0}
        
        mock_get_manager.return_value = websocket_manager
        mock_get_orchestrator.return_value = orchestrator

        # Start multiple concurrent integrations
        tasks = [
            bridge.ensure_integration(),
            bridge.ensure_integration(),
            bridge.ensure_integration()
        ]
        
        results = await asyncio.gather(*tasks)
        
        # All should succeed
        for result in results:
            assert result.success
            assert result.state == IntegrationState.ACTIVE

        # Should only initialize once
        assert bridge.metrics.total_initializations == 1

    async def test_clean_shutdown(self, bridge):
        """Test bridge shuts down cleanly."""
        # Start some background tasks
        await bridge.initialize()
        
        # Verify tasks started
        assert bridge._health_check_task is not None
        assert not bridge._health_check_task.done()
        
        # Shutdown
        await bridge.shutdown()
        
        # Verify clean shutdown
        assert bridge._shutdown
        assert bridge._health_check_task.done()
        assert bridge._websocket_manager is None
        assert bridge._orchestrator is None
        assert bridge.state == IntegrationState.UNINITIALIZED


@pytest.mark.asyncio
class TestAgentWebSocketBridgeMissionCritical:
    """Mission-critical tests for WebSocket event delivery - ensures business value."""

    @pytest.fixture
    async def bridge(self):
        """Create fresh bridge instance for each test."""
        AgentWebSocketBridge._instance = None
        bridge = AgentWebSocketBridge()
        yield bridge
        await bridge.shutdown()

    @pytest.fixture
    def mock_execution_context(self):
        """Mock execution context for testing."""
        context = Mock()
        context.user_id = "test_user"
        context.thread_id = "test_thread"
        context.run_id = "test_run"
        context.agent_name = "test_agent"
        return context

    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_agent_orchestrator')
    async def test_critical_event_delivery(self, mock_get_orchestrator, mock_get_manager, bridge, mock_execution_context):
        """Test critical WebSocket events are delivered for chat business value."""
        # Setup integration
        websocket_manager = AsyncMock()
        websocket_manager.send_to_thread.return_value = True
        orchestrator = AsyncMock()
        orchestrator.get_metrics.return_value = {"active_contexts": 0}
        
        mock_get_manager.return_value = websocket_manager
        mock_get_orchestrator.return_value = orchestrator

        # Initialize bridge
        result = await bridge.ensure_integration()
        assert result.success

        # Test critical event delivery
        success = await bridge.ensure_event_delivery(
            mock_execution_context,
            "agent_started",
            {"agent": "test_agent", "status": "processing"}
        )

        # Verify critical event delivered
        assert success
        websocket_manager.send_to_thread.assert_called_once()
        call_args = websocket_manager.send_to_thread.call_args
        assert call_args[0][0] == "test_thread"  # thread_id
        
        # Verify event structure
        event_payload = call_args[0][1]
        assert event_payload["type"] == "agent_started"
        assert "agent" in event_payload["payload"]

    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager')
    @patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_agent_orchestrator')
    async def test_event_delivery_retry_mechanism(self, mock_get_orchestrator, mock_get_manager, bridge, mock_execution_context):
        """Test event delivery retry mechanism for reliability."""
        # Setup integration with failing WebSocket manager
        websocket_manager = AsyncMock()
        websocket_manager.send_to_thread.side_effect = [False, False, True]  # Fail twice, succeed third time
        orchestrator = AsyncMock()
        orchestrator.get_metrics.return_value = {"active_contexts": 0}
        
        mock_get_manager.return_value = websocket_manager
        mock_get_orchestrator.return_value = orchestrator

        # Initialize bridge
        await bridge.ensure_integration()

        # Test event delivery with retries
        success = await bridge.ensure_event_delivery(
            mock_execution_context,
            "agent_thinking",
            {"message": "Processing request"}
        )

        # Verify event eventually delivered
        assert success
        assert websocket_manager.send_to_thread.call_count == 3  # Retried twice

    async def test_substantive_chat_value_preservation(self, bridge):
        """Test bridge preserves substantive chat value through WebSocket events."""
        # This test verifies that the bridge supports the business goal of substantive chat
        status = await bridge.get_status()
        
        # Bridge configuration should support chat business value
        assert status["config"]["event_delivery_timeout_ms"] <= 500  # Fast event delivery
        assert status["config"]["recovery_max_attempts"] >= 3  # Reliable recovery
        
        # Health monitoring should be frequent enough for chat
        assert status["config"]["health_check_interval_s"] <= 60  # Frequent health checks


if __name__ == "__main__":
    pytest.main([__file__, "-v"])