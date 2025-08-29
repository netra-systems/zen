"""
Comprehensive tests for Circuit Breaker Manager.

Tests circuit breaker state management, failure detection,
recovery mechanisms, and service monitoring.
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime, timedelta

from netra_backend.app.services.circuit_breaker.circuit_breaker_manager import (
    CircuitBreakerManager,
    CircuitBreakerConfig,
    ServiceConfig
)
from netra_backend.app.core.circuit_breaker_types import CircuitBreakerState


class TestCircuitBreakerManager:
    """Tests for circuit breaker manager functionality."""

    @pytest.fixture
    def manager(self):
        """Create a fresh circuit breaker manager for testing."""
        return CircuitBreakerManager()

    @pytest.fixture
    def service_config(self):
        """Create a test service configuration."""
        config = CircuitBreakerConfig(
            failure_threshold=3,
            recovery_timeout_seconds=30,
            half_open_max_calls=2,
            timeout_seconds=5.0
        )
        return ServiceConfig(
            name="test_service",
            endpoint="http://test-service:8080",
            health_check_url="http://test-service:8080/health",
            circuit_breaker_config=config
        )

    def test_manager_initialization(self, manager):
        """Test circuit breaker manager is properly initialized."""
        assert manager._circuit_breakers == {}
        assert manager._service_configs == {}
        assert manager._lock is not None
        assert manager._monitoring_task is None
        assert manager._running is False

    def test_circuit_breaker_config_defaults(self):
        """Test circuit breaker config has correct defaults."""
        config = CircuitBreakerConfig()
        
        assert config.failure_threshold == 5
        assert config.recovery_timeout_seconds == 60
        assert config.half_open_max_calls == 3
        assert config.timeout_seconds == 30.0

    def test_service_config_creation(self, service_config):
        """Test service config is created correctly."""
        assert service_config.name == "test_service"
        assert service_config.endpoint == "http://test-service:8080"
        assert service_config.health_check_url == "http://test-service:8080/health"
        assert service_config.circuit_breaker_config.failure_threshold == 3

    @pytest.mark.asyncio
    async def test_register_service(self, manager, service_config):
        """Test service registration creates circuit breaker."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_circuit_breaker = Mock()
            mock_cb.return_value = mock_circuit_breaker
            
            await manager.register_service(service_config)
            
            # Verify service was registered
            assert "test_service" in manager._service_configs
            assert manager._service_configs["test_service"] == service_config
            
            # Verify circuit breaker was created
            assert "test_service" in manager._circuit_breakers
            assert manager._circuit_breakers["test_service"] == mock_circuit_breaker

    @pytest.mark.asyncio
    async def test_duplicate_service_registration_updates(self, manager, service_config):
        """Test duplicate service registration updates configuration."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_cb.return_value = Mock()
            
            # Register service twice
            await manager.register_service(service_config)
            
            # Update config and re-register
            service_config.circuit_breaker_config.failure_threshold = 10
            await manager.register_service(service_config)
            
            # Should have updated config
            assert manager._service_configs["test_service"].circuit_breaker_config.failure_threshold == 10

    @pytest.mark.asyncio
    async def test_unregister_service(self, manager, service_config):
        """Test service unregistration removes circuit breaker."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_cb.return_value = Mock()
            
            await manager.register_service(service_config)
            assert "test_service" in manager._circuit_breakers
            
            await manager.unregister_service("test_service")
            
            assert "test_service" not in manager._circuit_breakers
            assert "test_service" not in manager._service_configs

    @pytest.mark.asyncio
    async def test_unregister_nonexistent_service_safe(self, manager):
        """Test unregistering non-existent service is safe."""
        # Should not raise exception
        await manager.unregister_service("nonexistent_service")

    @pytest.mark.asyncio
    async def test_execute_with_circuit_breaker_success(self, manager, service_config):
        """Test successful execution through circuit breaker."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_circuit_breaker = Mock()
            mock_circuit_breaker.call = AsyncMock(return_value="success_result")
            mock_cb.return_value = mock_circuit_breaker
            
            await manager.register_service(service_config)
            
            async def test_operation():
                return "success_result"
            
            result = await manager.execute_with_circuit_breaker(
                "test_service", 
                test_operation
            )
            
            assert result == "success_result"
            mock_circuit_breaker.call.assert_called_once_with(test_operation)

    @pytest.mark.asyncio
    async def test_execute_with_nonexistent_service_raises_error(self, manager):
        """Test execution with non-existent service raises error."""
        async def test_operation():
            return "result"
        
        with pytest.raises(ValueError) as exc_info:
            await manager.execute_with_circuit_breaker("unknown_service", test_operation)
        
        assert "not registered" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_circuit_breaker_state(self, manager, service_config):
        """Test getting circuit breaker state."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_circuit_breaker = Mock()
            mock_circuit_breaker.state = CircuitBreakerState.CLOSED
            mock_cb.return_value = mock_circuit_breaker
            
            await manager.register_service(service_config)
            
            state = await manager.get_circuit_breaker_state("test_service")
            
            assert state == CircuitBreakerState.CLOSED

    @pytest.mark.asyncio
    async def test_get_state_for_nonexistent_service_returns_none(self, manager):
        """Test getting state for non-existent service returns None."""
        state = await manager.get_circuit_breaker_state("unknown_service")
        assert state is None

    @pytest.mark.asyncio
    async def test_reset_circuit_breaker(self, manager, service_config):
        """Test resetting circuit breaker."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_circuit_breaker = Mock()
            mock_circuit_breaker.reset = AsyncMock()
            mock_cb.return_value = mock_circuit_breaker
            
            await manager.register_service(service_config)
            
            await manager.reset_circuit_breaker("test_service")
            
            mock_circuit_breaker.reset.assert_called_once()

    @pytest.mark.asyncio
    async def test_reset_nonexistent_circuit_breaker_safe(self, manager):
        """Test resetting non-existent circuit breaker is safe."""
        # Should not raise exception
        await manager.reset_circuit_breaker("unknown_service")

    @pytest.mark.asyncio
    async def test_get_all_service_states(self, manager):
        """Test getting states for all services."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            # Create multiple services
            services = ["service1", "service2", "service3"]
            expected_states = {}
            
            for i, service_name in enumerate(services):
                mock_circuit_breaker = Mock()
                mock_circuit_breaker.state = list(CircuitBreakerState)[i % 3]
                expected_states[service_name] = mock_circuit_breaker.state
                mock_cb.return_value = mock_circuit_breaker
                
                config = ServiceConfig(
                    name=service_name,
                    endpoint=f"http://{service_name}:8080"
                )
                await manager.register_service(config)
            
            states = await manager.get_all_service_states()
            
            assert len(states) == 3
            for service_name in services:
                assert service_name in states
                assert states[service_name] == expected_states[service_name]

    @pytest.mark.asyncio
    async def test_start_monitoring_starts_task(self, manager):
        """Test monitoring task is started."""
        with patch.object(manager, '_monitor_services') as mock_monitor:
            mock_monitor.return_value = asyncio.create_task(asyncio.sleep(0.1))
            
            await manager.start_monitoring()
            
            assert manager._running is True
            assert manager._monitoring_task is not None
            assert not manager._monitoring_task.done()

    @pytest.mark.asyncio
    async def test_stop_monitoring_cancels_task(self, manager):
        """Test monitoring task is cancelled when stopped."""
        # Start monitoring
        with patch.object(manager, '_monitor_services') as mock_monitor:
            mock_monitor.return_value = asyncio.create_task(asyncio.sleep(10))
            
            await manager.start_monitoring()
            monitoring_task = manager._monitoring_task
            
            # Stop monitoring
            await manager.stop_monitoring()
            
            assert manager._running is False
            assert monitoring_task.cancelled()

    @pytest.mark.asyncio
    async def test_monitoring_service_health_checks(self, manager, service_config):
        """Test monitoring performs health checks."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_circuit_breaker = Mock()
            mock_circuit_breaker.state = CircuitBreakerState.OPEN
            mock_cb.return_value = mock_circuit_breaker
            
            await manager.register_service(service_config)
            
            # Mock HTTP client for health checks
            with patch('aiohttp.ClientSession.get') as mock_get:
                mock_response = Mock()
                mock_response.status = 200
                mock_get.return_value.__aenter__.return_value = mock_response
                
                with patch.object(manager, '_check_service_health') as mock_health_check:
                    mock_health_check.return_value = True
                    
                    # Run a single monitoring cycle
                    await manager._monitor_services()
                    
                    mock_health_check.assert_called()

    @pytest.mark.asyncio
    async def test_health_check_success_resets_open_circuit(self, manager, service_config):
        """Test successful health check resets open circuit breaker."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_circuit_breaker = Mock()
            mock_circuit_breaker.state = CircuitBreakerState.OPEN
            mock_circuit_breaker.reset = AsyncMock()
            mock_cb.return_value = mock_circuit_breaker
            
            await manager.register_service(service_config)
            
            # Mock successful health check
            with patch.object(manager, '_check_service_health') as mock_health_check:
                mock_health_check.return_value = True
                
                await manager._handle_service_health("test_service", True)
                
                # Should reset circuit breaker
                mock_circuit_breaker.reset.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure_logs_error(self, manager, service_config):
        """Test failed health check is logged."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_circuit_breaker = Mock()
            mock_circuit_breaker.state = CircuitBreakerState.CLOSED
            mock_cb.return_value = mock_circuit_breaker
            
            await manager.register_service(service_config)
            
            with patch('netra_backend.app.services.circuit_breaker.circuit_breaker_manager.logger') as mock_logger:
                await manager._handle_service_health("test_service", False)
                
                # Should log health check failure
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_concurrent_service_operations(self, manager):
        """Test concurrent service operations are thread-safe."""
        configs = []
        for i in range(5):
            config = ServiceConfig(
                name=f"service_{i}",
                endpoint=f"http://service-{i}:8080"
            )
            configs.append(config)
        
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_cb.return_value = Mock()
            
            # Register services concurrently
            registration_tasks = [
                manager.register_service(config) for config in configs
            ]
            await asyncio.gather(*registration_tasks)
            
            # Verify all services registered
            assert len(manager._service_configs) == 5
            assert len(manager._circuit_breakers) == 5

    @pytest.mark.asyncio
    async def test_circuit_breaker_metrics_collection(self, manager, service_config):
        """Test circuit breaker metrics are collected."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_circuit_breaker = Mock()
            mock_circuit_breaker.get_metrics.return_value = {
                'failure_count': 2,
                'success_count': 10,
                'state_transitions': 3,
                'last_failure_time': datetime.now()
            }
            mock_cb.return_value = mock_circuit_breaker
            
            await manager.register_service(service_config)
            
            metrics = await manager.get_service_metrics("test_service")
            
            assert metrics is not None
            assert metrics['failure_count'] == 2
            assert metrics['success_count'] == 10
            assert metrics['state_transitions'] == 3

    @pytest.mark.asyncio
    async def test_bulk_circuit_breaker_operations(self, manager):
        """Test bulk operations on circuit breakers."""
        # Register multiple services
        service_names = ["service1", "service2", "service3"]
        
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_circuit_breaker = Mock()
            mock_circuit_breaker.reset = AsyncMock()
            mock_cb.return_value = mock_circuit_breaker
            
            for name in service_names:
                config = ServiceConfig(name=name, endpoint=f"http://{name}:8080")
                await manager.register_service(config)
            
            # Reset all circuit breakers
            await manager.reset_all_circuit_breakers()
            
            # Should have called reset on all circuit breakers
            assert mock_circuit_breaker.reset.call_count == len(service_names)

    @pytest.mark.asyncio
    async def test_circuit_breaker_state_transitions(self, manager, service_config):
        """Test circuit breaker state transitions are tracked."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_circuit_breaker = Mock()
            # Simulate state transitions
            states = [CircuitBreakerState.CLOSED, CircuitBreakerState.OPEN, CircuitBreakerState.HALF_OPEN]
            mock_circuit_breaker.state = states[0]
            mock_cb.return_value = mock_circuit_breaker
            
            await manager.register_service(service_config)
            
            # Track state changes
            state_history = []
            for state in states:
                mock_circuit_breaker.state = state
                current_state = await manager.get_circuit_breaker_state("test_service")
                state_history.append(current_state)
            
            assert state_history == states

    @pytest.mark.asyncio
    async def test_manager_shutdown_cleanup(self, manager, service_config):
        """Test manager shutdown cleans up resources."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_cb.return_value = Mock()
            
            # Register service and start monitoring
            await manager.register_service(service_config)
            await manager.start_monitoring()
            
            # Shutdown manager
            await manager.shutdown()
            
            assert manager._running is False
            assert manager._monitoring_task is None or manager._monitoring_task.cancelled()

    @pytest.mark.asyncio
    async def test_error_handling_in_monitoring(self, manager, service_config):
        """Test error handling in monitoring loop."""
        with patch('netra_backend.app.core.circuit_breaker.CircuitBreaker') as mock_cb:
            mock_cb.return_value = Mock()
            
            await manager.register_service(service_config)
            
            # Mock health check to raise exception
            with patch.object(manager, '_check_service_health') as mock_health_check:
                mock_health_check.side_effect = Exception("Health check failed")
                
                with patch('netra_backend.app.services.circuit_breaker.circuit_breaker_manager.logger') as mock_logger:
                    # Should not raise exception, but log error
                    await manager._monitor_services()
                    
                    mock_logger.error.assert_called()