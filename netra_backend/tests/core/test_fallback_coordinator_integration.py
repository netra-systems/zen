"""Integration and execution tests for FallbackCoordinator."""

from netra_backend.tests.test_utils import setup_test_path
setup_test_path()

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

# Add project root to path


# Import the components we're testing
from netra_backend.app.core.fallback_coordinator import FallbackCoordinator


class TestFallbackCoordinatorExecution:
    """Execution tests for FallbackCoordinator."""
    
    @pytest.fixture
    def coordinator(self):
        """Create a fresh FallbackCoordinator instance for testing."""
        with patch('app.core.fallback_coordinator.HealthMonitor') as mock_health_monitor, \
             patch('app.core.fallback_coordinator.EmergencyFallbackManager') as mock_emergency_manager:
            
            # Create mock instances
            mock_health_instance = Mock()
            mock_health_instance.is_emergency_mode_active = AsyncMock(return_value=False)
            mock_health_instance.should_prevent_cascade = AsyncMock(return_value=False)
            mock_health_instance.record_success = AsyncMock()
            mock_health_instance.record_failure = AsyncMock()
            mock_health_instance.update_circuit_breaker_status = AsyncMock()
            mock_health_instance.update_system_health = AsyncMock()
            mock_health_instance.get_system_status = Mock(return_value={"status": "healthy"})
            mock_health_instance.system_health_history = []
            
            mock_emergency_instance = Mock()
            mock_emergency_instance.execute_emergency_fallback = AsyncMock(return_value={"emergency": True})
            mock_emergency_instance.execute_limited_fallback = AsyncMock(return_value={"limited": True})
            
            mock_health_monitor.return_value = mock_health_instance
            mock_emergency_manager.return_value = mock_emergency_instance
            
            coordinator = FallbackCoordinator()
            coordinator.health_monitor = mock_health_instance
            coordinator.emergency_manager = mock_emergency_instance
            
            return coordinator
    
    async def test_execute_with_coordination_success(self, coordinator):
        """Test successful operation execution with coordination."""
        # Setup
        agent_name = "TestAgent"
        operation_name = "test_operation"
        
        async def mock_operation():
            return {"success": True}
        
        # Setup agent handler
        mock_handler = AsyncMock()
        mock_handler.execute_with_fallback.return_value = {"success": True}
        coordinator.agent_handlers[agent_name] = mock_handler
        
        # Execute
        result = await coordinator.execute_with_coordination(
            agent_name, mock_operation, operation_name
        )
        
        # Verify result
        assert result == {"success": True}
        
        # Verify handler was called correctly
        mock_handler.execute_with_fallback.assert_called_once_with(
            mock_operation, operation_name, agent_name, "general"
        )
        
        # Verify success was recorded
        coordinator.health_monitor.record_success.assert_called_once_with(agent_name)
    
    async def test_execute_with_coordination_emergency_mode(self, coordinator):
        """Test execution during emergency mode."""
        # Setup emergency mode
        coordinator.health_monitor.is_emergency_mode_active.return_value = True
        
        agent_name = "TestAgent"
        operation_name = "test_operation"
        
        async def mock_operation():
            return {"success": True}
        
        # Execute
        result = await coordinator.execute_with_coordination(
            agent_name, mock_operation, operation_name, "critical"
        )
        
        # Verify emergency fallback was used
        assert result == {"emergency": True}
        coordinator.emergency_manager.execute_emergency_fallback.assert_called_once_with(
            agent_name, operation_name, "critical"
        )
    
    async def test_execute_with_coordination_cascade_prevention(self, coordinator):
        """Test execution with cascade prevention active."""
        # Setup cascade prevention
        coordinator.health_monitor.should_prevent_cascade.return_value = True
        
        agent_name = "TestAgent"
        operation_name = "test_operation"
        
        async def mock_operation():
            return {"success": True}
        
        # Execute
        result = await coordinator.execute_with_coordination(
            agent_name, mock_operation, operation_name
        )
        
        # Verify limited fallback was used
        assert result == {"limited": True}
        coordinator.emergency_manager.execute_limited_fallback.assert_called_once_with(
            agent_name, operation_name
        )
    
    async def test_execute_with_coordination_unregistered_agent(self, coordinator):
        """Test execution with unregistered agent."""
        agent_name = "UnregisteredAgent"
        operation_name = "test_operation"
        
        async def mock_operation():
            return {"success": True}
        
        # Execute and verify exception
        with pytest.raises(ValueError, match="Agent UnregisteredAgent not registered"):
            await coordinator.execute_with_coordination(
                agent_name, mock_operation, operation_name
            )
    
    async def test_execute_with_coordination_failure(self, coordinator):
        """Test execution with operation failure."""
        # Setup
        agent_name = "TestAgent"
        operation_name = "test_operation"
        test_error = ValueError("Operation failed")
        
        async def mock_operation():
            raise test_error
        
        # Setup agent handler to raise error
        mock_handler = AsyncMock()
        mock_handler.execute_with_fallback.side_effect = test_error
        coordinator.agent_handlers[agent_name] = mock_handler
        
        # Execute and verify exception propagates
        with pytest.raises(ValueError, match="Operation failed"):
            await coordinator.execute_with_coordination(
                agent_name, mock_operation, operation_name
            )
        
        # Verify failure was recorded
        coordinator.health_monitor.record_failure.assert_called_once_with(agent_name, test_error)
        coordinator.health_monitor.update_circuit_breaker_status.assert_called_once_with(agent_name)
        coordinator.health_monitor.update_system_health.assert_called_once()
    
    async def test_execute_with_coordination_custom_fallback_type(self, coordinator):
        """Test execution with custom fallback type."""
        agent_name = "TestAgent"
        operation_name = "test_operation"
        fallback_type = "critical"
        
        async def mock_operation():
            return {"success": True}
        
        # Setup agent handler
        mock_handler = AsyncMock()
        mock_handler.execute_with_fallback.return_value = {"success": True}
        coordinator.agent_handlers[agent_name] = mock_handler
        
        # Execute
        await coordinator.execute_with_coordination(
            agent_name, mock_operation, operation_name, fallback_type
        )
        
        # Verify custom fallback type was passed
        mock_handler.execute_with_fallback.assert_called_once_with(
            mock_operation, operation_name, agent_name, fallback_type
        )
    
    async def test_concurrent_operations(self, coordinator):
        """Test concurrent operations on different agents."""
        # Setup multiple agents
        agents = ["Agent1", "Agent2", "Agent3"]
        handlers = {}
        
        for agent in agents:
            mock_handler = AsyncMock()
            mock_handler.execute_with_fallback.return_value = f"result_{agent}"
            coordinator.agent_handlers[agent] = mock_handler
            handlers[agent] = mock_handler
        
        async def mock_operation(agent_name):
            return f"operation_{agent_name}"
        
        # Execute operations concurrently
        tasks = [
            coordinator.execute_with_coordination(
                agent, lambda a=agent: mock_operation(a), f"operation_{agent}"
            )
            for agent in agents
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all operations completed
        assert len(results) == 3
        for i, agent in enumerate(agents):
            assert results[i] == f"result_{agent}"
            handlers[agent].execute_with_fallback.assert_called_once()
    
    async def test_error_handling_in_health_monitoring(self, coordinator):
        """Test error handling when health monitoring fails."""
        agent_name = "TestAgent"
        test_error = ValueError("Test error")
        
        # Setup handler to succeed but health monitoring to fail
        mock_handler = AsyncMock()
        mock_handler.execute_with_fallback.return_value = {"success": True}
        coordinator.agent_handlers[agent_name] = mock_handler
        
        # Make health monitoring fail
        coordinator.health_monitor.record_success.side_effect = Exception("Health monitoring failed")
        
        async def mock_operation():
            return {"success": True}
        
        # Execute - should still work despite health monitoring failure
        with pytest.raises(Exception, match="Health monitoring failed"):
            await coordinator.execute_with_coordination(
                agent_name, mock_operation, "test_operation"
            )
        
        # Handler should still have been called
        mock_handler.execute_with_fallback.assert_called_once()


class TestFallbackCoordinatorIntegration:
    """Integration tests for FallbackCoordinator with mock dependencies."""
    
    @pytest.fixture
    def full_coordinator(self):
        """Create coordinator with full mock setup."""
        with patch('app.core.fallback_coordinator.LLMFallbackHandler') as mock_handler_class, \
             patch('app.core.fallback_coordinator.CircuitBreaker') as mock_cb_class, \
             patch('app.core.fallback_coordinator.HealthMonitor') as mock_health_class, \
             patch('app.core.fallback_coordinator.EmergencyFallbackManager') as mock_emergency_class:
            
            coordinator = FallbackCoordinator()
            return coordinator, mock_handler_class, mock_cb_class, mock_health_class, mock_emergency_class
    
    async def test_full_workflow_success(self, full_coordinator):
        """Test complete workflow from registration to execution."""
        coordinator, mock_handler_class, mock_cb_class, mock_health_class, mock_emergency_class = full_coordinator
        
        # Setup mocks
        mock_handler = AsyncMock()
        mock_handler.execute_with_fallback.return_value = {"success": True, "data": "test_result"}
        mock_handler_class.return_value = mock_handler
        
        # Register agent
        agent_name = "TestAgent"
        handler = coordinator.register_agent(agent_name)
        
        # Verify registration
        assert handler == mock_handler
        assert coordinator.is_agent_registered(agent_name)
        assert agent_name in coordinator.get_registered_agents()
        
        # Execute operation
        async def test_operation():
            return {"raw": "data"}
        
        result = await coordinator.execute_with_coordination(
            agent_name, test_operation, "test_operation", "standard"
        )
        
        # Verify execution
        assert result == {"success": True, "data": "test_result"}
        mock_handler.execute_with_fallback.assert_called_once_with(
            test_operation, "test_operation", agent_name, "standard"
        )
        
        # Verify health monitoring
        coordinator.health_monitor.record_success.assert_called_once_with(agent_name)
    
    async def test_full_workflow_with_failure_and_reset(self, full_coordinator):
        """Test workflow including failure handling and reset."""
        coordinator, mock_handler_class, mock_cb_class, mock_health_class, mock_emergency_class = full_coordinator
        
        # Setup mocks
        mock_handler = AsyncMock()
        test_error = RuntimeError("Execution failed")
        mock_handler.execute_with_fallback.side_effect = test_error
        mock_handler_class.return_value = mock_handler
        
        mock_cb = Mock()
        mock_cb_class.return_value = mock_cb
        
        # Register agent
        agent_name = "TestAgent"
        coordinator.register_agent(agent_name)
        
        # Execute operation with failure
        async def failing_operation():
            raise test_error
        
        with pytest.raises(RuntimeError, match="Execution failed"):
            await coordinator.execute_with_coordination(
                agent_name, failing_operation, "failing_operation"
            )
        
        # Verify failure was recorded
        coordinator.health_monitor.record_failure.assert_called_once_with(agent_name, test_error)
        coordinator.health_monitor.update_circuit_breaker_status.assert_called_once_with(agent_name)
        coordinator.health_monitor.update_system_health.assert_called_once()
        
        # Reset agent status
        reset_result = await coordinator.reset_agent_status(agent_name)
        assert reset_result is True
        
        # Verify reset operations
        mock_cb.reset.assert_called_once()
        mock_handler.reset_circuit_breakers.assert_called_once()
