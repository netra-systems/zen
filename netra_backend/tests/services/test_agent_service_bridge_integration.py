from unittest.mock import Mock, AsyncMock, patch, MagicMock
"""
Integration tests for AgentService with AgentWebSocketBridge.

Tests the complete integration between AgentService and the bridge,
ensuring clean boundaries and proper coordination.
"""

import asyncio
import pytest
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.services.agent_service_core import AgentService
from netra_backend.app.services.agent_websocket_bridge import (
AgentWebSocketBridge,
IntegrationState
)
from netra_backend.app import schemas


class TestAgentServiceBridgeIntegration:
    """Integration tests for AgentService with bridge coordination."""
    pass

    @pytest.fixture
    def real_supervisor():
        """Use real service instance."""
    # TODO: Initialize real service
        """Mock supervisor agent."""
        pass
        supervisor = supervisor_instance  # Initialize appropriate service
        supervisor.registry = registry_instance  # Initialize appropriate service
        supervisor.registry.websocket_manager = None
        supervisor.registry.set_websocket_manager = UnifiedWebSocketManager()
        supervisor.run = AsyncMock(return_value="Agent response")
        return supervisor

    @pytest.fixture
    async def clean_service(self, mock_supervisor):
        """Create clean AgentService instance."""
        # Reset bridge singleton
        AgentWebSocketBridge._instance = None

        # Create service (will initialize bridge in background)
        service = AgentService(mock_supervisor)

        # Allow bridge initialization to complete
        await asyncio.sleep(0.1)

        yield service

        # Cleanup
        if service._bridge:
            await service._bridge.shutdown()

            async def test_service_bridge_initialization(self, mock_get_registry, mock_get_manager, clean_service):
                """Test AgentService properly initializes bridge integration."""
                pass
        # Setup mocks
                websocket_manager = AsyncNone  # TODO: Use real service instance
                registry = AsyncNone  # TODO: Use real service instance
                registry.get_metrics.return_value = {"active_contexts": 0}

                mock_get_manager.return_value = websocket_manager
                mock_get_registry.return_value = registry

        # Wait for bridge initialization to complete
                await asyncio.sleep(0.2)

        # Ensure service readiness
                ready = await clean_service.ensure_service_ready()
                assert ready

        # Verify bridge is initialized
                assert clean_service._bridge is not None
                assert clean_service._bridge_initialized

        # Verify bridge state
                status = await clean_service._bridge.get_status()
                assert status["state"] == "active"

                async def test_service_status_includes_bridge(self, mock_get_registry, mock_get_manager, clean_service):
                    """Test AgentService status includes bridge integration status."""
        # Setup mocks
                    websocket_manager = AsyncNone  # TODO: Use real service instance
                    registry = AsyncNone  # TODO: Use real service instance
                    registry.get_metrics.return_value = {"active_contexts": 0}

                    mock_get_manager.return_value = websocket_manager
                    mock_get_registry.return_value = registry

        # Wait for initialization
                    await asyncio.sleep(0.2)
                    await clean_service.ensure_service_ready()

        # Get service status
                    status = await clean_service.get_agent_status("test_user")

        # Verify bridge status included
                    assert "service_ready" in status
                    assert "bridge_integrated" in status
                    assert "websocket_integration" in status
                    assert "websocket_healthy" in status
                    assert "registry_healthy" in status

        # Verify positive integration status
                    assert status["bridge_integrated"]
                    assert status["websocket_integration"] == "active"

                    async def test_comprehensive_service_status(self, mock_get_registry, mock_get_manager, clean_service):
                        """Test comprehensive service status provides full observability."""
                        pass
        # Setup mocks
                        websocket_manager = AsyncNone  # TODO: Use real service instance
                        registry = AsyncNone  # TODO: Use real service instance
                        registry.get_metrics.return_value = {"active_contexts": 0}

                        mock_get_manager.return_value = websocket_manager
                        mock_get_registry.return_value = registry

        # Wait for initialization
                        await asyncio.sleep(0.2)
                        await clean_service.ensure_service_ready()

        # Get comprehensive status
                        status = await clean_service.get_comprehensive_status()

        # Verify service sections
                        assert status["service"] == "AgentService"
                        assert "supervisor" in status
                        assert "thread_service" in status
                        assert "message_handler" in status
                        assert "bridge" in status

        # Verify bridge section provides full metrics
                        bridge_status = status["bridge"]
                        assert "state" in bridge_status
                        assert "health" in bridge_status
                        assert "metrics" in bridge_status
                        assert "config" in bridge_status
                        assert "dependencies" in bridge_status

                        async def test_agent_execution_with_bridge(self, mock_get_registry, mock_get_manager, clean_service, mock_supervisor):
                            """Test agent execution coordinates properly with bridge."""
        # Setup mocks for successful integration
                            websocket_manager = AsyncNone  # TODO: Use real service instance
                            registry = AsyncNone  # TODO: Use real service instance
                            registry.get_metrics.return_value = {"active_contexts": 0}
                            registry.create_execution_context = AsyncNone  # TODO: Use real service instance
                            registry.complete_execution = AsyncNone  # TODO: Use real service instance

        # Mock execution context and notifier
                            mock_context = mock_context_instance  # Initialize appropriate service
                            mock_context.thread_id = "test_thread"
                            mock_context.run_id = "test_run"
                            mock_notifier = AsyncNone  # TODO: Use real service instance

                            registry.create_execution_context.return_value = (mock_context, mock_notifier)

                            mock_get_manager.return_value = websocket_manager
                            mock_get_registry.return_value = registry

        # Wait for initialization
                            await asyncio.sleep(0.2)
                            await clean_service.ensure_service_ready()

        # Execute agent
                            result = await clean_service.execute_agent(
                            agent_type="test_agent",
                            message="test message",
                            context={"test": "context"},
                            user_id="test_user"
                            )

        # Verify successful execution with bridge coordination
                            assert result["status"] == "success"
                            assert result["bridge_coordinated"]
                            assert result["websocket_events_sent"]
                            assert result["agent"] == "test_agent"

        # Verify bridge coordination calls
                            registry.create_execution_context.assert_called_once()
                            mock_notifier.send_agent_thinking.assert_called_once()
                            registry.complete_execution.assert_called_once()

        # Verify supervisor was called with proper message
                            mock_supervisor.run.assert_called_once()
                            call_args = mock_supervisor.run.call_args[0]
                            assert "[Agent Type: test_agent]" in call_args[0]
                            assert "test message" in call_args[0]

                            async def test_agent_execution_fallback(self, mock_get_manager, clean_service, mock_supervisor):
                                """Test agent execution falls back gracefully when bridge unavailable."""
                                pass
        # Setup failing WebSocket manager to trigger fallback
                                mock_get_manager.side_effect = RuntimeError("WebSocket unavailable")

        # Wait for initialization (will fail)
                                await asyncio.sleep(0.2)

        # Execute agent (should use fallback)
                                result = await clean_service.execute_agent(
                                agent_type="test_agent",
                                message="test message",
                                user_id="test_user"
                                )

        # Verify fallback execution
                                assert result["status"] == "success"
                                assert not result["bridge_coordinated"]
                                assert not result["websocket_events_sent"]
                                assert result["fallback_execution"]

        # Verify supervisor was still called
                                mock_supervisor.run.assert_called_once()

                                async def test_service_boundary_separation(self, clean_service):
                                    """Test clean boundary separation between service and bridge."""
        # AgentService should have agent-specific methods
                                    service_methods = [method for method in dir(clean_service) if not method.startswith('_')]

                                    expected_agent_methods = [
                                    'run', 'start_agent', 'stop_agent', 'execute_agent',
                                    'handle_websocket_message', 'process_message', 'generate_stream'
                                    ]

                                    for method in expected_agent_methods:
                                        assert method in service_methods, f"AgentService missing method: {method}"

        # AgentService should NOT have bridge-specific methods
                                        bridge_methods = ['ensure_integration', 'recover_integration', 'track_connection_health']

                                        for method in bridge_methods:
                                            assert method not in service_methods, f"AgentService should not have bridge method: {method}"

                                            async def test_idempotent_service_readiness(self, mock_get_registry, mock_get_manager, clean_service):
                                                """Test service readiness check is idempotent."""
                                                pass
        # Setup mocks
                                                websocket_manager = AsyncNone  # TODO: Use real service instance
                                                registry = AsyncNone  # TODO: Use real service instance
                                                registry.get_metrics.return_value = {"active_contexts": 0}

                                                mock_get_manager.return_value = websocket_manager
                                                mock_get_registry.return_value = registry

        # Multiple readiness checks should be safe
                                                ready1 = await clean_service.ensure_service_ready()
                                                ready2 = await clean_service.ensure_service_ready()
                                                ready3 = await clean_service.ensure_service_ready()

        # All should succeed
                                                assert ready1
                                                assert ready2
                                                assert ready3

        # Bridge should only initialize once
                                                assert clean_service._bridge.metrics.total_initializations <= 1

                                                async def test_bridge_recovery_integration(self, mock_get_registry, mock_get_manager, clean_service):
                                                    """Test service can recover from bridge failures."""
        # Setup initially failing, then succeeding mocks
                                                    mock_get_manager.side_effect = [
                                                    RuntimeError("Initial failure"),
                                                    AsyncNone  # TODO: Use real service instance  # Recovery succeeds
                                                    ]
                                                    registry = AsyncNone  # TODO: Use real service instance
                                                    registry.get_metrics.return_value = {"active_contexts": 0}
                                                    mock_get_registry.return_value = registry

        # Wait for initial setup (will fail)
                                                    await asyncio.sleep(0.2)

        # First readiness check should fail
                                                    ready1 = await clean_service.ensure_service_ready()
                                                    assert not ready1

        # Bridge should recover automatically
                                                    ready2 = await clean_service.ensure_service_ready()
                                                    assert ready2

        # Verify bridge recovered
                                                    status = await clean_service._bridge.get_status()
                                                    assert status["state"] == "active"

                                                    async def test_message_handler_bridge_integration(self, clean_service):
                                                        """Test message handler gets configured with bridge-managed WebSocket."""
                                                        pass
        # Initially message handler might not have WebSocket manager
                                                        initial_manager = getattr(clean_service.message_handler, '_websocket_manager', None)

        # Ensure service ready (will configure message handler)
                                                        with patch('netra_backend.app.services.agent_websocket_bridge.get_websocket_manager') as mock_get_manager, \
                                                        patch('netra_backend.app.services.agent_websocket_bridge.get_agent_execution_registry') as mock_get_registry:
                                                            pass

                                                            websocket_manager = AsyncNone  # TODO: Use real service instance
                                                            registry = AsyncNone  # TODO: Use real service instance
                                                            registry.get_metrics.return_value = {"active_contexts": 0}

                                                            mock_get_manager.return_value = websocket_manager
                                                            mock_get_registry.return_value = registry

                                                            await clean_service.ensure_service_ready()

            # Message handler should now have bridge-managed WebSocket manager
                                                            assert hasattr(clean_service.message_handler, '_websocket_manager')
            # Should be the same manager from bridge
                                                            assert clean_service.message_handler._websocket_manager is clean_service._bridge._websocket_manager


                                                            class TestAgentServiceLegacyCompatibility:
                                                                """Tests ensuring backward compatibility during bridge integration."""
                                                                pass

                                                                @pytest.fixture
                                                                def real_supervisor():
                                                                    """Use real service instance."""
    # TODO: Initialize real service
                                                                    """Mock supervisor agent."""
                                                                    pass
                                                                    supervisor = supervisor_instance  # Initialize appropriate service
                                                                    supervisor.registry = registry_instance  # Initialize appropriate service
                                                                    supervisor.run = AsyncMock(return_value="Legacy response")
                                                                    # FIXED: await outside async - using pass
                                                                    pass
                                                                    return supervisor

                                                                async def test_constructor_signature_unchanged(self, mock_supervisor):
                                                                    """Test AgentService constructor signature remains compatible."""
        # Should still accept just supervisor
                                                                    service = AgentService(mock_supervisor)

        # Basic attributes should be initialized
                                                                    assert service.supervisor is mock_supervisor
                                                                    assert service.thread_service is not None
                                                                    assert service.message_handler is not None

        # Cleanup
                                                                    if service._bridge:
                                                                        await service._bridge.shutdown()

                                                                        async def test_graceful_degradation(self, mock_get_manager, mock_supervisor):
                                                                            """Test service works even if bridge initialization fails."""
                                                                            pass
        # Setup bridge initialization to fail
                                                                            mock_get_manager.side_effect = RuntimeError("No WebSocket available")

        # Create service
                                                                            service = AgentService(mock_supervisor)
                                                                            await asyncio.sleep(0.2)  # Allow initialization attempt

        # Basic service operations should still work
                                                                            request = schemas.RequestModel(query="test", id="test_id", user_request="test")

        # This should not raise - should use fallback paths
                                                                            result = await service.run(request, "test_run")
                                                                            assert result is not None

        # Cleanup
                                                                            if service._bridge:
                                                                                await service._bridge.shutdown()

                                                                                async def test_existing_methods_preserved(self, mock_supervisor):
                                                                                    """Test all existing public methods are preserved."""
                                                                                    service = AgentService(mock_supervisor)

        # List of methods that should still exist for backward compatibility
                                                                                    expected_methods = [
                                                                                    'run', 'start_agent', 'stop_agent', 'get_agent_status',
                                                                                    'handle_websocket_message', 'process_message', 'generate_stream'
                                                                                    ]

                                                                                    service_methods = [method for method in dir(service) if not method.startswith('_')]

                                                                                    for method in expected_methods:
                                                                                        assert method in service_methods, f"Method {method} should be preserved for compatibility"
                                                                                        assert callable(getattr(service, method)), f"Method {method} should be callable"

        # Cleanup
                                                                                        if service._bridge:
                                                                                            await service._bridge.shutdown()


                                                                                            if __name__ == "__main__":
                                                                                                pytest.main([__file__, "-v"])
                                                                                                pass