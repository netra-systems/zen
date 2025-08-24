"""Core functionality tests for FallbackCoordinator."""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Import the components we're testing
from netra_backend.app.core.fallback_coordinator import FallbackCoordinator

class TestFallbackCoordinator:
    """Core tests for FallbackCoordinator."""
    
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
    
    def test_initialization(self, coordinator):
        """Test proper initialization of FallbackCoordinator."""
        assert isinstance(coordinator.agent_handlers, dict)
        assert isinstance(coordinator.agent_circuit_breakers, dict)
        assert isinstance(coordinator.agent_statuses, dict)
        
        # Check default settings
        assert coordinator.max_concurrent_fallbacks == 3
        assert coordinator.cascade_prevention_threshold == 0.5
        assert coordinator.emergency_mode_threshold == 0.7
        
        # Check sub-managers exist
        assert coordinator.health_monitor is not None
        assert coordinator.emergency_manager is not None
    
    @patch('app.core.fallback_coordinator.LLMFallbackHandler')
    @patch('app.core.fallback_coordinator.CircuitBreaker')
    @patch('app.core.fallback_coordinator.AgentFallbackStatus')
    def test_register_agent_new(self, mock_status, mock_circuit_breaker, mock_handler, coordinator):
        """Test registering a new agent."""
        # Setup mocks
        mock_handler_instance = Mock()
        mock_handler.return_value = mock_handler_instance
        
        mock_cb_instance = Mock()
        mock_circuit_breaker.return_value = mock_cb_instance
        
        mock_status_instance = Mock()
        mock_status.return_value = mock_status_instance
        
        # Register agent
        result = coordinator.register_agent("TestAgent")
        
        # Verify handler was created and returned
        assert result == mock_handler_instance
        assert "TestAgent" in coordinator.agent_handlers
        assert coordinator.agent_handlers["TestAgent"] == mock_handler_instance
        
        # Verify circuit breaker was created
        assert "TestAgent" in coordinator.agent_circuit_breakers
        assert coordinator.agent_circuit_breakers["TestAgent"] == mock_cb_instance
        
        # Verify status was initialized
        assert "TestAgent" in coordinator.agent_statuses
        assert coordinator.agent_statuses["TestAgent"] == mock_status_instance
        
        # Verify handler was called with default config
        mock_handler.assert_called_once()
        
        # Verify circuit breaker was created with correct config
        mock_circuit_breaker.assert_called_once()
        cb_config = mock_circuit_breaker.call_args[0][0]
        assert cb_config.failure_threshold == 3
        assert cb_config.recovery_timeout == 60.0
        assert cb_config.name == "coordinator_TestAgent"
    
    def test_register_agent_already_exists(self, coordinator):
        """Test registering an agent that already exists."""
        # Setup existing agent
        existing_handler = Mock()
        coordinator.agent_handlers["TestAgent"] = existing_handler
        
        with patch('app.core.fallback_coordinator.logger') as mock_logger:
            result = coordinator.register_agent("TestAgent")
            
            # Should return existing handler
            assert result == existing_handler
            
            # Should log warning
            mock_logger.warning.assert_called_once()
    
    @patch('app.core.fallback_coordinator.FallbackConfig')
    def test_register_agent_with_custom_config(self, mock_config, coordinator):
        """Test registering agent with custom fallback config."""
        custom_config = Mock()
        
        with patch('app.core.fallback_coordinator.LLMFallbackHandler') as mock_handler, \
             patch('app.core.fallback_coordinator.CircuitBreaker'), \
             patch('app.core.fallback_coordinator.AgentFallbackStatus'):
            
            coordinator.register_agent("TestAgent", custom_config)
            
            # Verify custom config was used
            mock_handler.assert_called_once_with(custom_config)
    
    def test_get_default_fallback_config(self, coordinator):
        """Test default fallback configuration."""
        config = coordinator._get_default_fallback_config()
        
        assert config.max_retries == 2
        assert config.base_delay == 1.0
        assert config.max_delay == 15.0
        assert config.timeout == 30.0
        assert config.use_circuit_breaker is True
    
    def test_get_system_status(self, coordinator):
        """Test getting system status."""
        status = coordinator.get_system_status()
        
        assert status == {"status": "healthy"}
        coordinator.health_monitor.get_system_status.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_reset_agent_status_success(self, coordinator):
        """Test resetting agent status successfully."""
        agent_name = "TestAgent"
        
        # Setup agent components
        mock_cb = Mock()
        mock_handler = Mock()
        mock_status = Mock()
        
        coordinator.agent_circuit_breakers[agent_name] = mock_cb
        coordinator.agent_handlers[agent_name] = mock_handler
        coordinator.agent_statuses[agent_name] = mock_status
        
        with patch('app.core.fallback_coordinator.AgentFallbackStatus') as mock_status_class:
            mock_new_status = Mock()
            mock_status_class.return_value = mock_new_status
            
            # Reset
            result = await coordinator.reset_agent_status(agent_name)
            
            # Verify success
            assert result is True
            
            # Verify reset operations
            mock_cb.reset.assert_called_once()
            mock_handler.reset_circuit_breakers.assert_called_once()
            
            # Verify new status was created
            mock_status_class.assert_called_once_with(
                agent_name=agent_name,
                circuit_breaker_open=False,
                recent_failures=0,
                fallback_active=False,
                last_failure_time=None,
                health_score=1.0
            )
            assert coordinator.agent_statuses[agent_name] == mock_new_status
    
    @pytest.mark.asyncio
    async def test_reset_agent_status_unregistered(self, coordinator):
        """Test resetting status for unregistered agent."""
        result = await coordinator.reset_agent_status("UnregisteredAgent")
        assert result is False
    
    @pytest.mark.asyncio
    async def test_reset_system_status(self, coordinator):
        """Test resetting entire system status."""
        # Setup multiple agents
        coordinator.agent_statuses = {
            "Agent1": Mock(),
            "Agent2": Mock(),
            "Agent3": Mock()
        }
        
        with patch.object(coordinator, 'reset_agent_status', new=AsyncMock()) as mock_reset:
            await coordinator.reset_system_status()
            
            # Verify all agents were reset
            assert mock_reset.call_count == 3
            mock_reset.assert_any_call("Agent1")
            mock_reset.assert_any_call("Agent2")
            mock_reset.assert_any_call("Agent3")
            
            # Verify health history was cleared
            assert len(coordinator.health_monitor.system_health_history) == 0
    
    def test_get_agent_handler_exists(self, coordinator):
        """Test getting handler for existing agent."""
        agent_name = "TestAgent"
        mock_handler = Mock()
        coordinator.agent_handlers[agent_name] = mock_handler
        
        result = coordinator.get_agent_handler(agent_name)
        assert result == mock_handler
    
    def test_get_agent_handler_not_exists(self, coordinator):
        """Test getting handler for non-existing agent."""
        result = coordinator.get_agent_handler("NonExistentAgent")
        assert result is None
    
    def test_get_registered_agents(self, coordinator):
        """Test getting list of registered agents."""
        # Setup agents
        coordinator.agent_handlers = {
            "Agent1": Mock(),
            "Agent2": Mock(),
            "Agent3": Mock()
        }
        
        result = coordinator.get_registered_agents()
        assert set(result) == {"Agent1", "Agent2", "Agent3"}
        assert len(result) == 3
    
    def test_get_registered_agents_empty(self, coordinator):
        """Test getting registered agents when none exist."""
        result = coordinator.get_registered_agents()
        assert result == []
    
    def test_is_agent_registered_true(self, coordinator):
        """Test checking if agent is registered - positive case."""
        coordinator.agent_handlers["TestAgent"] = Mock()
        assert coordinator.is_agent_registered("TestAgent") is True
    
    def test_is_agent_registered_false(self, coordinator):
        """Test checking if agent is registered - negative case."""
        assert coordinator.is_agent_registered("NonExistentAgent") is False
    
    def test_multiple_agent_registration(self, coordinator):
        """Test registering multiple agents."""
        agents = ["Agent1", "Agent2", "Agent3"]
        
        with patch('app.core.fallback_coordinator.LLMFallbackHandler') as mock_handler, \
             patch('app.core.fallback_coordinator.CircuitBreaker'), \
             patch('app.core.fallback_coordinator.AgentFallbackStatus'):
            
            handlers = []
            for agent in agents:
                handler = coordinator.register_agent(agent)
                handlers.append(handler)
            
            # Verify all agents registered
            assert len(coordinator.agent_handlers) == 3
            assert len(coordinator.agent_circuit_breakers) == 3
            assert len(coordinator.agent_statuses) == 3
            
            for agent in agents:
                assert agent in coordinator.agent_handlers
                assert agent in coordinator.agent_circuit_breakers
                assert agent in coordinator.agent_statuses
    
    @pytest.mark.asyncio
    async def test_reset_agent_status_partial_components(self, coordinator):
        """Test resetting agent status when some components don't exist."""
        agent_name = "TestAgent"
        
        # Only add status, missing circuit breaker and handler
        coordinator.agent_statuses[agent_name] = Mock()
        
        with patch('app.core.fallback_coordinator.AgentFallbackStatus') as mock_status_class:
            mock_new_status = Mock()
            mock_status_class.return_value = mock_new_status
            
            # Should still succeed without circuit breaker or handler
            result = await coordinator.reset_agent_status(agent_name)
            
            assert result is True
            assert coordinator.agent_statuses[agent_name] == mock_new_status
    
    def test_coordinator_settings_modification(self, coordinator):
        """Test modifying coordinator settings."""
        # Modify settings
        coordinator.max_concurrent_fallbacks = 5
        coordinator.cascade_prevention_threshold = 0.6
        coordinator.emergency_mode_threshold = 0.8
        
        # Verify changes
        assert coordinator.max_concurrent_fallbacks == 5
        assert coordinator.cascade_prevention_threshold == 0.6
        assert coordinator.emergency_mode_threshold == 0.8
