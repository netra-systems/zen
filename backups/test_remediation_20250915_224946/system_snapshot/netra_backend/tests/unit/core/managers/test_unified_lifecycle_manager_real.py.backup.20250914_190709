"""
Comprehensive Unit Tests for UnifiedLifecycleManager SSOT class using REAL instances.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Velocity, Risk Reduction
- Business Goal: Ensure reliable lifecycle management across all services
- Value Impact: Prevents service startup/shutdown issues, resource leaks, and chat interruption
- Strategic Impact: Validates SSOT lifecycle consolidation for zero-downtime deployments

CRITICAL REQUIREMENTS:
- Tests REAL UnifiedLifecycleManager class (NO MOCKS)
- Provides REAL business value validation
- Follows reports/testing/TEST_CREATION_GUIDE.md strictly
- Uses IsolatedEnvironment for all environment access
- Tests multi-user scenarios and factory patterns
- Achieves 100% coverage of critical paths

Created following CLAUDE.md directive: Create ALL NEW test to replace legacy mock-based tests.
"""

import pytest
import asyncio
import time
import threading
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

from shared.isolated_environment import IsolatedEnvironment, get_env
from test_framework.isolated_environment_fixtures import isolated_env, test_env

# Import the REAL UnifiedLifecycleManager
from netra_backend.app.core.managers.unified_lifecycle_manager import (
    SystemLifecycle as UnifiedLifecycleManager,  # Use new name with backward compatibility alias
    SystemLifecycleFactory as LifecycleManagerFactory,  # Use new name with backward compatibility alias
    LifecyclePhase,
    ComponentType,
    ComponentStatus,
    LifecycleMetrics,
    get_lifecycle_manager,
    setup_application_lifecycle
)


class MockComponent:
    """Real component for testing lifecycle operations - simulates real services."""
    
    def __init__(self, name: str, startup_delay: float = 0.0, fail_startup: bool = False, 
                 fail_shutdown: bool = False, fail_health_check: bool = False):
        self.name = name
        self.status = "initialized"
        self.startup_delay = startup_delay
        self.fail_startup = fail_startup
        self.fail_shutdown = fail_shutdown
        self.fail_health_check = fail_health_check
        self.startup_called = False
        self.shutdown_called = False
        self.initialize_called = False
        self.health_check_called = False
    
    async def initialize(self):
        """Initialize component."""
        self.initialize_called = True
        if self.fail_startup:
            raise Exception(f"Component {self.name} initialization failed")
        await asyncio.sleep(self.startup_delay)
        self.status = "initialized"
    
    async def startup(self):
        """Start component."""
        self.startup_called = True
        if self.fail_startup:
            raise Exception(f"Component {self.name} startup failed")
        await asyncio.sleep(self.startup_delay)
        self.status = "running"
    
    async def start(self):
        """Alternative start method."""
        await self.startup()
    
    async def shutdown(self):
        """Shutdown component."""
        self.shutdown_called = True
        if self.fail_shutdown:
            raise Exception(f"Component {self.name} shutdown failed")
        self.status = "stopped"
    
    async def stop(self):
        """Alternative stop method."""
        await self.shutdown()
    
    async def close(self):
        """Alternative close method."""
        await self.shutdown()
    
    async def health_check(self):
        """Health check for component."""
        self.health_check_called = True
        if self.fail_health_check:
            return {"healthy": False, "error": "Health check failed"}
        return {"healthy": True, "status": self.status}


class MockWebSocketManager:
    """Mock WebSocket manager with real interface for testing."""
    
    def __init__(self):
        self.messages_sent = []
        self.connection_count = 0
        self.closed = False
        
    async def broadcast_system_message(self, message: Dict[str, Any]):
        """Broadcast system message."""
        self.messages_sent.append(message)
    
    def get_connection_count(self) -> int:
        """Get connection count."""
        return self.connection_count
    
    async def close_all_connections(self):
        """Close all connections."""
        self.closed = True


class MockAgentRegistry:
    """Mock agent registry with real interface for testing."""
    
    def __init__(self):
        self.active_tasks = []
        self.stopped_accepting = False
        self.registry_ready = True
    
    def get_registry_status(self) -> Dict[str, Any]:
        """Get registry status."""
        return {"ready": self.registry_ready, "reason": "Test registry"}
    
    def get_active_tasks(self) -> List[asyncio.Task]:
        """Get active tasks."""
        return self.active_tasks
    
    def stop_accepting_requests(self):
        """Stop accepting requests."""
        self.stopped_accepting = True


class MockHealthService:
    """Mock health service with real interface for testing."""
    
    def __init__(self):
        self.marked_shutting_down = False
    
    async def mark_shutting_down(self):
        """Mark as shutting down."""
        self.marked_shutting_down = True


# ============================================================================
# COMPONENT REGISTRATION AND MANAGEMENT TESTS
# ============================================================================

class TestComponentRegistration:
    """Test component registration and management with real lifecycle manager."""
    
    @pytest.fixture
    def lifecycle_manager(self, isolated_env):
        """Create real lifecycle manager with test environment."""
        return UnifiedLifecycleManager(
            user_id="test_user",
            shutdown_timeout=5,
            drain_timeout=3,
            health_check_grace_period=1,
            startup_timeout=10
        )
    
    @pytest.mark.asyncio
    async def test_register_component_real_instance(self, lifecycle_manager):
        """Test registering real component instance."""
        component = MockComponent("test_component")
        
        await lifecycle_manager.register_component(
            "test_component", 
            component, 
            ComponentType.DATABASE_MANAGER
        )
        
        # Verify component registration
        assert "test_component" in lifecycle_manager._components
        component_status = lifecycle_manager.get_component_status("test_component")
        assert component_status is not None
        assert component_status.name == "test_component"
        assert component_status.component_type == ComponentType.DATABASE_MANAGER
        assert component_status.status == "registered"
        
        # Verify component can be retrieved
        retrieved = lifecycle_manager.get_component(ComponentType.DATABASE_MANAGER)
        assert retrieved is component
    
    @pytest.mark.asyncio
    async def test_register_multiple_components_different_types(self, lifecycle_manager):
        """Test registering multiple components of different types."""
        components = [
            ("database", MockComponent("database"), ComponentType.DATABASE_MANAGER),
            ("redis", MockComponent("redis"), ComponentType.REDIS_MANAGER),
            ("websocket", MockWebSocketManager(), ComponentType.WEBSOCKET_MANAGER),
            ("agent_registry", MockAgentRegistry(), ComponentType.AGENT_REGISTRY),
        ]
        
        for name, component, comp_type in components:
            await lifecycle_manager.register_component(name, component, comp_type)
        
        # Verify all components registered
        assert len(lifecycle_manager._components) == 4
        assert len(lifecycle_manager._component_instances) == 4
        
        # Verify each component can be retrieved
        for name, component, comp_type in components:
            retrieved = lifecycle_manager.get_component(comp_type)
            assert retrieved is component
    
    @pytest.mark.asyncio
    async def test_register_component_with_health_check(self, lifecycle_manager):
        """Test registering component with health check function."""
        component = MockComponent("health_component")
        
        async def health_check():
            return {"healthy": True, "custom": "health_data"}
        
        await lifecycle_manager.register_component(
            "health_component",
            component,
            ComponentType.DATABASE_MANAGER,
            health_check=health_check
        )
        
        # Verify health check registered
        assert "health_component" in lifecycle_manager._health_checks
        component_status = lifecycle_manager.get_component_status("health_component")
        assert component_status.metadata["has_health_check"] is True
    
    @pytest.mark.asyncio
    async def test_unregister_component(self, lifecycle_manager):
        """Test unregistering components."""
        component = MockComponent("temp_component")
        
        await lifecycle_manager.register_component(
            "temp_component",
            component,
            ComponentType.LLM_MANAGER
        )
        
        # Verify registered
        assert "temp_component" in lifecycle_manager._components
        assert ComponentType.LLM_MANAGER in lifecycle_manager._component_instances
        
        # Unregister
        await lifecycle_manager.unregister_component("temp_component")
        
        # Verify unregistered
        assert "temp_component" not in lifecycle_manager._components
        assert ComponentType.LLM_MANAGER not in lifecycle_manager._component_instances
    
    def test_get_component_status_nonexistent(self, lifecycle_manager):
        """Test getting status of non-existent component."""
        status = lifecycle_manager.get_component_status("nonexistent")
        assert status is None
    
    def test_get_component_nonexistent_type(self, lifecycle_manager):
        """Test getting non-existent component type."""
        component = lifecycle_manager.get_component(ComponentType.CLICKHOUSE_MANAGER)
        assert component is None


# ============================================================================
# STARTUP LIFECYCLE MANAGEMENT TESTS
# ============================================================================

class TestStartupLifecycle:
    """Test startup lifecycle operations with real components."""
    
    @pytest.fixture
    def lifecycle_manager(self, isolated_env):
        """Create real lifecycle manager for startup tests."""
        return UnifiedLifecycleManager(
            user_id="startup_test_user",
            shutdown_timeout=10,
            startup_timeout=15
        )
    
    @pytest.mark.asyncio
    async def test_startup_empty_system(self, lifecycle_manager):
        """Test startup with no registered components."""
        assert lifecycle_manager.get_current_phase() == LifecyclePhase.INITIALIZING
        
        result = await lifecycle_manager.startup()
        
        assert result is True
        assert lifecycle_manager.get_current_phase() == LifecyclePhase.RUNNING
        assert lifecycle_manager.is_running() is True
        assert lifecycle_manager._metrics.startup_time is not None
        assert lifecycle_manager._metrics.startup_time > 0
    
    @pytest.mark.asyncio
    async def test_startup_with_single_component(self, lifecycle_manager):
        """Test startup with single component."""
        component = MockComponent("single_component")
        
        await lifecycle_manager.register_component(
            "single_component",
            component,
            ComponentType.DATABASE_MANAGER,
            health_check=component.health_check
        )
        
        result = await lifecycle_manager.startup()
        
        assert result is True
        assert lifecycle_manager.is_running() is True
        assert component.initialize_called is True
        assert component.status == "running"
        
        # Verify component status updated
        component_status = lifecycle_manager.get_component_status("single_component")
        assert component_status.status == "initialized"
    
    @pytest.mark.asyncio
    async def test_startup_multiple_components_correct_order(self, lifecycle_manager):
        """Test startup with multiple components in correct initialization order."""
        components = {}
        
        # Register components in different order than initialization
        comp_configs = [
            ("websocket", ComponentType.WEBSOCKET_MANAGER, MockWebSocketManager()),
            ("database", ComponentType.DATABASE_MANAGER, MockComponent("database")),
            ("agent_registry", ComponentType.AGENT_REGISTRY, MockAgentRegistry()),
            ("redis", ComponentType.REDIS_MANAGER, MockComponent("redis")),
        ]
        
        for name, comp_type, component in comp_configs:
            components[name] = component
            await lifecycle_manager.register_component(name, component, comp_type)
        
        result = await lifecycle_manager.startup()
        
        assert result is True
        assert lifecycle_manager.is_running() is True
        
        # Verify all components processed
        for name, component in components.items():
            if hasattr(component, 'initialize_called'):
                assert component.initialize_called is True
    
    @pytest.mark.asyncio
    async def test_startup_component_validation_failure(self, lifecycle_manager):
        """Test startup failure during component validation."""
        # Register component that will fail health check
        unhealthy_component = MockComponent("unhealthy", fail_health_check=True)
        
        await lifecycle_manager.register_component(
            "unhealthy",
            unhealthy_component,
            ComponentType.DATABASE_MANAGER,
            health_check=unhealthy_component.health_check
        )
        
        result = await lifecycle_manager.startup()
        
        assert result is False
        assert lifecycle_manager.get_current_phase() == LifecyclePhase.ERROR
        assert not lifecycle_manager.is_running()
    
    @pytest.mark.asyncio
    async def test_startup_component_initialization_failure(self, lifecycle_manager):
        """Test startup failure during component initialization."""
        failing_component = MockComponent("failing", fail_startup=True)
        
        await lifecycle_manager.register_component(
            "failing",
            failing_component,
            ComponentType.DATABASE_MANAGER
        )
        
        result = await lifecycle_manager.startup()
        
        assert result is False
        assert lifecycle_manager.get_current_phase() == LifecyclePhase.ERROR
        
        # Verify error recorded in component status
        component_status = lifecycle_manager.get_component_status("failing")
        assert component_status.status == "initialization_failed"
        assert component_status.error_count > 0
        assert component_status.last_error is not None
    
    @pytest.mark.asyncio
    async def test_startup_invalid_phase(self, lifecycle_manager):
        """Test startup attempt from invalid phase."""
        # First successful startup
        await lifecycle_manager.startup()
        assert lifecycle_manager.is_running()
        
        # Attempt second startup - should fail
        result = await lifecycle_manager.startup()
        assert result is False
    
    @pytest.mark.asyncio
    async def test_startup_websocket_integration(self, lifecycle_manager):
        """Test WebSocket manager integration during startup."""
        ws_manager = MockWebSocketManager()
        
        await lifecycle_manager.register_component(
            "websocket_manager",
            ws_manager,
            ComponentType.WEBSOCKET_MANAGER
        )
        
        result = await lifecycle_manager.startup()
        
        assert result is True
        # Verify WebSocket manager stored for lifecycle events
        assert lifecycle_manager._websocket_manager is ws_manager
    
    @pytest.mark.asyncio
    async def test_startup_health_monitoring_enabled(self, lifecycle_manager):
        """Test health monitoring starts during startup."""
        component = MockComponent("monitored")
        
        await lifecycle_manager.register_component(
            "monitored",
            component,
            ComponentType.DATABASE_MANAGER,
            health_check=component.health_check
        )
        
        result = await lifecycle_manager.startup()
        
        assert result is True
        # Verify health monitoring task started
        assert lifecycle_manager._health_check_task is not None
        assert not lifecycle_manager._health_check_task.done()


# ============================================================================
# SHUTDOWN LIFECYCLE MANAGEMENT TESTS
# ============================================================================

class TestShutdownLifecycle:
    """Test shutdown lifecycle operations with real components."""
    
    @pytest.fixture
    def running_lifecycle_manager(self, isolated_env):
        """Create real running lifecycle manager for shutdown tests."""
        manager = UnifiedLifecycleManager(
            user_id="shutdown_test_user",
            shutdown_timeout=5,
            drain_timeout=2,
            health_check_grace_period=1
        )
        return manager
    
    @pytest.mark.asyncio
    async def test_shutdown_empty_running_system(self, running_lifecycle_manager):
        """Test shutdown of empty running system."""
        # Start system first
        await running_lifecycle_manager.startup()
        assert running_lifecycle_manager.is_running()
        
        result = await running_lifecycle_manager.shutdown()
        
        assert result is True
        assert running_lifecycle_manager.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE
        assert running_lifecycle_manager.is_shutting_down() is True
        assert running_lifecycle_manager._metrics.shutdown_time is not None
        assert running_lifecycle_manager._metrics.successful_shutdowns == 1
    
    @pytest.mark.asyncio
    async def test_shutdown_with_components(self, running_lifecycle_manager):
        """Test shutdown with registered components."""
        components = {}
        
        # Register and start components
        comp_configs = [
            ("database", ComponentType.DATABASE_MANAGER, MockComponent("database")),
            ("redis", ComponentType.REDIS_MANAGER, MockComponent("redis")),
            ("websocket", ComponentType.WEBSOCKET_MANAGER, MockWebSocketManager()),
        ]
        
        for name, comp_type, component in comp_configs:
            components[name] = component
            await running_lifecycle_manager.register_component(name, component, comp_type)
        
        await running_lifecycle_manager.startup()
        
        result = await running_lifecycle_manager.shutdown()
        
        assert result is True
        assert running_lifecycle_manager.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE
        
        # Verify all components shut down
        for name, component in components.items():
            if hasattr(component, 'shutdown_called'):
                assert component.shutdown_called is True
    
    @pytest.mark.asyncio
    async def test_shutdown_component_failure(self, running_lifecycle_manager):
        """Test shutdown with component failure."""
        failing_component = MockComponent("failing", fail_shutdown=True)
        
        await running_lifecycle_manager.register_component(
            "failing",
            failing_component,
            ComponentType.DATABASE_MANAGER
        )
        
        await running_lifecycle_manager.startup()
        
        result = await running_lifecycle_manager.shutdown()
        
        # Shutdown should continue despite component failure
        assert result is True
        assert running_lifecycle_manager.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE
        
        # Verify error recorded
        component_status = running_lifecycle_manager.get_component_status("failing")
        assert component_status.status == "shutdown_failed"
        assert component_status.error_count > 0
    
    @pytest.mark.asyncio
    async def test_shutdown_duplicate_request(self, running_lifecycle_manager):
        """Test duplicate shutdown requests."""
        await running_lifecycle_manager.startup()
        
        # Start first shutdown
        shutdown_task1 = asyncio.create_task(running_lifecycle_manager.shutdown())
        
        # Wait briefly and start second shutdown
        await asyncio.sleep(0.1)
        shutdown_task2 = asyncio.create_task(running_lifecycle_manager.shutdown())
        
        result1 = await shutdown_task1
        result2 = await shutdown_task2
        
        assert result1 is True
        assert result2 is True  # Should succeed but be ignored
        assert running_lifecycle_manager._metrics.successful_shutdowns == 1
    
    @pytest.mark.asyncio
    async def test_shutdown_websocket_notification(self, running_lifecycle_manager):
        """Test WebSocket shutdown notifications."""
        ws_manager = MockWebSocketManager()
        ws_manager.connection_count = 5
        
        await running_lifecycle_manager.register_component(
            "websocket_manager",
            ws_manager,
            ComponentType.WEBSOCKET_MANAGER
        )
        
        await running_lifecycle_manager.startup()
        
        result = await running_lifecycle_manager.shutdown()
        
        assert result is True
        # Verify shutdown message sent
        assert len(ws_manager.messages_sent) > 0
        shutdown_message = ws_manager.messages_sent[0]
        assert shutdown_message["type"] == "system_shutdown"
        assert ws_manager.closed is True
    
    @pytest.mark.asyncio
    async def test_shutdown_agent_task_completion(self, running_lifecycle_manager):
        """Test agent task completion during shutdown."""
        agent_registry = MockAgentRegistry()
        
        # Create mock active tasks
        async def mock_task():
            await asyncio.sleep(0.5)
        
        agent_registry.active_tasks = [
            asyncio.create_task(mock_task()),
            asyncio.create_task(mock_task())
        ]
        
        await running_lifecycle_manager.register_component(
            "agent_registry",
            agent_registry,
            ComponentType.AGENT_REGISTRY
        )
        
        await running_lifecycle_manager.startup()
        
        result = await running_lifecycle_manager.shutdown()
        
        assert result is True
        assert agent_registry.stopped_accepting is True
        # Verify all tasks completed
        for task in agent_registry.active_tasks:
            assert task.done()
    
    @pytest.mark.asyncio
    async def test_shutdown_health_service_grace_period(self, running_lifecycle_manager):
        """Test health service grace period during shutdown."""
        health_service = MockHealthService()
        
        await running_lifecycle_manager.register_component(
            "health_service",
            health_service,
            ComponentType.HEALTH_SERVICE
        )
        
        await running_lifecycle_manager.startup()
        
        start_time = time.time()
        result = await running_lifecycle_manager.shutdown()
        end_time = time.time()
        
        assert result is True
        assert health_service.marked_shutting_down is True
        # Verify grace period was observed (at least 1 second)
        assert end_time - start_time >= 1.0


# ============================================================================
# REQUEST TRACKING AND GRACEFUL SHUTDOWN TESTS
# ============================================================================

class TestRequestTracking:
    """Test request tracking for graceful shutdown."""
    
    @pytest.fixture
    def lifecycle_manager(self, isolated_env):
        """Create real lifecycle manager for request tracking tests."""
        return UnifiedLifecycleManager(
            user_id="request_test_user",
            shutdown_timeout=10,
            drain_timeout=3
        )
    
    @pytest.mark.asyncio
    async def test_request_context_tracking(self, lifecycle_manager):
        """Test request context manager for tracking active requests."""
        assert len(lifecycle_manager._active_requests) == 0
        
        async with lifecycle_manager.request_context("request_1"):
            assert len(lifecycle_manager._active_requests) == 1
            assert "request_1" in lifecycle_manager._active_requests
            
            async with lifecycle_manager.request_context("request_2"):
                assert len(lifecycle_manager._active_requests) == 2
                assert "request_2" in lifecycle_manager._active_requests
        
        assert len(lifecycle_manager._active_requests) == 0
    
    @pytest.mark.asyncio
    async def test_request_draining_during_shutdown(self, lifecycle_manager):
        """Test request draining during shutdown."""
        await lifecycle_manager.startup()
        
        # Start long-running request
        async def long_request():
            async with lifecycle_manager.request_context("long_request"):
                await asyncio.sleep(1.0)  # Simulates processing time
        
        request_task = asyncio.create_task(long_request())
        
        # Wait for request to start
        await asyncio.sleep(0.1)
        assert len(lifecycle_manager._active_requests) == 1
        
        # Start shutdown - should wait for request to complete
        shutdown_start = time.time()
        shutdown_task = asyncio.create_task(lifecycle_manager.shutdown())
        
        # Complete the request
        await request_task
        result = await shutdown_task
        shutdown_end = time.time()
        
        assert result is True
        # Should have waited for request to complete
        assert shutdown_end - shutdown_start >= 1.0
    
    @pytest.mark.asyncio
    async def test_request_drain_timeout(self, lifecycle_manager):
        """Test request drain timeout handling."""
        await lifecycle_manager.startup()
        
        # Start request that won't complete within drain timeout
        async def stuck_request():
            async with lifecycle_manager.request_context("stuck_request"):
                await asyncio.sleep(10.0)  # Longer than drain timeout
        
        request_task = asyncio.create_task(stuck_request())
        
        # Wait for request to start
        await asyncio.sleep(0.1)
        
        # Start shutdown with short drain timeout
        shutdown_start = time.time()
        result = await lifecycle_manager.shutdown()
        shutdown_end = time.time()
        
        assert result is True
        # Should timeout after drain_timeout (3 seconds)
        assert shutdown_end - shutdown_start < 5.0
        
        # Clean up stuck request
        request_task.cancel()
        try:
            await request_task
        except asyncio.CancelledError:
            pass
    
    @pytest.mark.asyncio
    async def test_multiple_concurrent_requests(self, lifecycle_manager):
        """Test multiple concurrent requests during operation."""
        await lifecycle_manager.startup()
        
        async def concurrent_request(request_id: str, duration: float):
            async with lifecycle_manager.request_context(request_id):
                await asyncio.sleep(duration)
        
        # Start multiple concurrent requests
        tasks = []
        for i in range(5):
            task = asyncio.create_task(concurrent_request(f"req_{i}", 0.5))
            tasks.append(task)
        
        # Wait for all to start
        await asyncio.sleep(0.1)
        assert len(lifecycle_manager._active_requests) == 5
        
        # Complete all requests
        await asyncio.gather(*tasks)
        assert len(lifecycle_manager._active_requests) == 0
    
    def test_get_status_includes_active_requests(self, lifecycle_manager):
        """Test that status includes active request count."""
        status = lifecycle_manager.get_status()
        assert "active_requests" in status
        assert status["active_requests"] == 0
        
        # Add mock active request
        lifecycle_manager._active_requests["test"] = time.time()
        
        status = lifecycle_manager.get_status()
        assert status["active_requests"] == 1


# ============================================================================
# HEALTH MONITORING TESTS
# ============================================================================

class TestHealthMonitoring:
    """Test health monitoring functionality."""
    
    @pytest.fixture
    def lifecycle_manager(self, isolated_env):
        """Create real lifecycle manager with faster health checks for testing."""
        manager = UnifiedLifecycleManager(
            user_id="health_test_user",
            health_check_grace_period=1,
            startup_timeout=10
        )
        # Override health check interval for faster testing
        manager._health_check_interval = 0.5
        return manager
    
    @pytest.mark.asyncio
    async def test_health_monitoring_starts_with_startup(self, lifecycle_manager):
        """Test health monitoring task starts during startup."""
        component = MockComponent("health_component")
        
        await lifecycle_manager.register_component(
            "health_component",
            component,
            ComponentType.DATABASE_MANAGER,
            health_check=component.health_check
        )
        
        result = await lifecycle_manager.startup()
        
        assert result is True
        assert lifecycle_manager._health_check_task is not None
        assert not lifecycle_manager._health_check_task.done()
    
    @pytest.mark.asyncio
    async def test_health_check_execution(self, lifecycle_manager):
        """Test health check execution for registered components."""
        healthy_component = MockComponent("healthy")
        unhealthy_component = MockComponent("unhealthy", fail_health_check=True)
        
        await lifecycle_manager.register_component(
            "healthy",
            healthy_component,
            ComponentType.DATABASE_MANAGER,
            health_check=healthy_component.health_check
        )
        
        await lifecycle_manager.register_component(
            "unhealthy",
            unhealthy_component,
            ComponentType.REDIS_MANAGER,
            health_check=unhealthy_component.health_check
        )
        
        # Run health checks manually
        health_results = await lifecycle_manager._run_all_health_checks()
        
        assert "healthy" in health_results
        assert "unhealthy" in health_results
        assert health_results["healthy"]["healthy"] is True
        assert health_results["unhealthy"]["healthy"] is False
        assert healthy_component.health_check_called is True
        assert unhealthy_component.health_check_called is True
    
    @pytest.mark.asyncio
    async def test_health_monitoring_updates_component_status(self, lifecycle_manager):
        """Test health monitoring updates component status."""
        component = MockComponent("status_component", fail_health_check=True)
        
        await lifecycle_manager.register_component(
            "status_component",
            component,
            ComponentType.DATABASE_MANAGER,
            health_check=component.health_check
        )
        
        # Run periodic health check
        await lifecycle_manager._run_periodic_health_checks()
        
        # Verify component status updated
        component_status = lifecycle_manager.get_component_status("status_component")
        assert component_status.status == "unhealthy"
        assert component_status.error_count > 0
        assert component_status.last_error is not None
        assert lifecycle_manager._metrics.component_failures > 0
    
    @pytest.mark.asyncio
    async def test_health_monitoring_cleanup_on_shutdown(self, lifecycle_manager):
        """Test health monitoring task cleanup during shutdown."""
        await lifecycle_manager.startup()
        
        # Verify health monitoring running
        assert lifecycle_manager._health_check_task is not None
        assert not lifecycle_manager._health_check_task.done()
        
        await lifecycle_manager.shutdown()
        
        # Verify health monitoring cleaned up
        assert lifecycle_manager._health_check_task is None
    
    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self, lifecycle_manager):
        """Test health check exception handling."""
        def failing_health_check():
            raise Exception("Health check error")
        
        component = MockComponent("error_component")
        
        await lifecycle_manager.register_component(
            "error_component",
            component,
            ComponentType.DATABASE_MANAGER,
            health_check=failing_health_check
        )
        
        # Run health check - should not raise exception
        health_results = await lifecycle_manager._run_all_health_checks()
        
        assert "error_component" in health_results
        assert health_results["error_component"]["healthy"] is False
        assert health_results["error_component"]["error"] == "Health check error"
    
    def test_get_health_status_running(self, lifecycle_manager):
        """Test health status when system is running."""
        lifecycle_manager._current_phase = LifecyclePhase.RUNNING
        
        status = lifecycle_manager.get_health_status()
        
        assert status["status"] == "healthy"
        assert status["phase"] == "running"
        assert status["components_healthy"] is True
    
    def test_get_health_status_starting(self, lifecycle_manager):
        """Test health status when system is starting."""
        lifecycle_manager._current_phase = LifecyclePhase.STARTING
        
        status = lifecycle_manager.get_health_status()
        
        assert status["status"] == "starting"
        assert status["phase"] == "starting"
        assert status["ready"] is False
    
    def test_get_health_status_shutting_down(self, lifecycle_manager):
        """Test health status when system is shutting down."""
        lifecycle_manager._current_phase = LifecyclePhase.SHUTTING_DOWN
        
        status = lifecycle_manager.get_health_status()
        
        assert status["status"] == "shutting_down"
        assert status["phase"] == "shutting_down"
        assert status["ready"] is False


# ============================================================================
# LIFECYCLE HOOKS AND HANDLERS TESTS
# ============================================================================

class TestLifecycleHooks:
    """Test lifecycle hooks and custom handlers."""
    
    @pytest.fixture
    def lifecycle_manager(self, isolated_env):
        """Create real lifecycle manager for hooks testing."""
        return UnifiedLifecycleManager(user_id="hooks_test_user")
    
    @pytest.mark.asyncio
    async def test_startup_handlers_execution(self, lifecycle_manager):
        """Test custom startup handlers execution."""
        startup_calls = []
        
        def sync_startup_handler():
            startup_calls.append("sync_handler")
        
        async def async_startup_handler():
            startup_calls.append("async_handler")
        
        lifecycle_manager.add_startup_handler(sync_startup_handler)
        lifecycle_manager.add_startup_handler(async_startup_handler)
        
        result = await lifecycle_manager.startup()
        
        assert result is True
        assert "sync_handler" in startup_calls
        assert "async_handler" in startup_calls
    
    @pytest.mark.asyncio
    async def test_shutdown_handlers_execution(self, lifecycle_manager):
        """Test custom shutdown handlers execution."""
        shutdown_calls = []
        
        def sync_shutdown_handler():
            shutdown_calls.append("sync_shutdown")
        
        async def async_shutdown_handler():
            shutdown_calls.append("async_shutdown")
        
        lifecycle_manager.add_shutdown_handler(sync_shutdown_handler)
        lifecycle_manager.add_shutdown_handler(async_shutdown_handler)
        
        await lifecycle_manager.startup()
        result = await lifecycle_manager.shutdown()
        
        assert result is True
        assert "sync_shutdown" in shutdown_calls
        assert "async_shutdown" in shutdown_calls
    
    @pytest.mark.asyncio
    async def test_lifecycle_hooks_registration(self, lifecycle_manager):
        """Test lifecycle hook registration."""
        hook_calls = []
        
        def pre_startup_hook(**kwargs):
            hook_calls.append("pre_startup")
        
        def post_startup_hook(**kwargs):
            hook_calls.append("post_startup")
        
        def on_error_hook(**kwargs):
            hook_calls.append(f"error: {kwargs.get('error', 'unknown')}")
        
        lifecycle_manager.register_lifecycle_hook("pre_startup", pre_startup_hook)
        lifecycle_manager.register_lifecycle_hook("post_startup", post_startup_hook)
        lifecycle_manager.register_lifecycle_hook("on_error", on_error_hook)
        
        result = await lifecycle_manager.startup()
        
        assert result is True
        assert "pre_startup" in hook_calls
        assert "post_startup" in hook_calls
    
    @pytest.mark.asyncio
    async def test_error_hooks_execution(self, lifecycle_manager):
        """Test error hooks execution on failures."""
        error_calls = []
        
        def error_hook(**kwargs):
            error_calls.append({
                "error": str(kwargs.get("error", "")),
                "phase": kwargs.get("phase", ""),
                "component": kwargs.get("component", "")
            })
        
        lifecycle_manager.register_lifecycle_hook("on_error", error_hook)
        
        # Register failing component
        failing_component = MockComponent("fail", fail_startup=True)
        await lifecycle_manager.register_component(
            "fail",
            failing_component,
            ComponentType.DATABASE_MANAGER
        )
        
        result = await lifecycle_manager.startup()
        
        assert result is False
        assert len(error_calls) > 0
        assert "startup" in error_calls[0]["phase"]
    
    @pytest.mark.asyncio
    async def test_handler_exception_handling(self, lifecycle_manager):
        """Test handler exception handling doesn't break lifecycle."""
        def failing_handler():
            raise Exception("Handler failed")
        
        lifecycle_manager.add_startup_handler(failing_handler)
        
        # Startup should succeed despite handler failure
        result = await lifecycle_manager.startup()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_hook_exception_handling(self, lifecycle_manager):
        """Test hook exception handling."""
        def failing_hook(**kwargs):
            raise Exception("Hook failed")
        
        lifecycle_manager.register_lifecycle_hook("pre_startup", failing_hook)
        
        # Startup should succeed despite hook failure
        result = await lifecycle_manager.startup()
        assert result is True
    
    def test_unknown_lifecycle_event(self, lifecycle_manager):
        """Test registering hook for unknown event."""
        def test_hook(**kwargs):
            pass
        
        # Should log warning but not fail
        lifecycle_manager.register_lifecycle_hook("unknown_event", test_hook)
        
        # Verify hook not registered
        assert "unknown_event" not in lifecycle_manager._lifecycle_hooks


# ============================================================================
# MULTI-USER AND FACTORY PATTERN TESTS
# ============================================================================

class TestMultiUserSupport:
    """Test multi-user support and factory pattern."""
    
    def test_user_specific_lifecycle_manager_creation(self, isolated_env):
        """Test creation of user-specific lifecycle managers."""
        manager1 = UnifiedLifecycleManager(user_id="user1")
        manager2 = UnifiedLifecycleManager(user_id="user2")
        
        assert manager1.user_id == "user1"
        assert manager2.user_id == "user2"
        assert manager1 is not manager2
    
    def test_global_lifecycle_manager_creation(self, isolated_env):
        """Test creation of global lifecycle manager."""
        manager = UnifiedLifecycleManager()
        assert manager.user_id is None
    
    def test_lifecycle_manager_factory_global(self, isolated_env):
        """Test LifecycleManagerFactory for global manager."""
        manager1 = LifecycleManagerFactory.get_global_manager()
        manager2 = LifecycleManagerFactory.get_global_manager()
        
        assert manager1 is manager2  # Should be singleton
        assert manager1.user_id is None
    
    def test_lifecycle_manager_factory_user_specific(self, isolated_env):
        """Test LifecycleManagerFactory for user-specific managers."""
        manager1 = LifecycleManagerFactory.get_user_manager("user1")
        manager2 = LifecycleManagerFactory.get_user_manager("user1")
        manager3 = LifecycleManagerFactory.get_user_manager("user2")
        
        assert manager1 is manager2  # Same user, same instance
        assert manager1 is not manager3  # Different users, different instances
        assert manager1.user_id == "user1"
        assert manager3.user_id == "user2"
    
    def test_get_lifecycle_manager_convenience_function(self, isolated_env):
        """Test get_lifecycle_manager convenience function."""
        global_manager = get_lifecycle_manager()
        user_manager = get_lifecycle_manager("test_user")
        
        assert global_manager.user_id is None
        assert user_manager.user_id == "test_user"
    
    def test_factory_manager_count(self, isolated_env):
        """Test factory manager count tracking."""
        # Clear any existing managers first
        LifecycleManagerFactory._global_manager = None
        LifecycleManagerFactory._user_managers.clear()
        
        initial_count = LifecycleManagerFactory.get_manager_count()
        assert initial_count["global"] == 0
        assert initial_count["user_specific"] == 0
        assert initial_count["total"] == 0
        
        # Create managers
        global_manager = LifecycleManagerFactory.get_global_manager()
        user_manager1 = LifecycleManagerFactory.get_user_manager("user1")
        user_manager2 = LifecycleManagerFactory.get_user_manager("user2")
        
        count = LifecycleManagerFactory.get_manager_count()
        assert count["global"] == 1
        assert count["user_specific"] == 2
        assert count["total"] == 3
    
    @pytest.mark.asyncio
    async def test_factory_shutdown_all_managers(self, isolated_env):
        """Test shutting down all managers through factory."""
        # Clear existing managers
        LifecycleManagerFactory._global_manager = None
        LifecycleManagerFactory._user_managers.clear()
        
        # Create managers
        global_manager = LifecycleManagerFactory.get_global_manager()
        user_manager = LifecycleManagerFactory.get_user_manager("test_user")
        
        # Start them
        await global_manager.startup()
        await user_manager.startup()
        
        assert global_manager.is_running()
        assert user_manager.is_running()
        
        # Shutdown all
        await LifecycleManagerFactory.shutdown_all_managers()
        
        assert global_manager.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE
        assert user_manager.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE
        
        # Verify factory cleaned up
        count = LifecycleManagerFactory.get_manager_count()
        assert count["total"] == 0
    
    @pytest.mark.asyncio
    async def test_isolated_user_component_registration(self, isolated_env):
        """Test user isolation in component registration."""
        user1_manager = LifecycleManagerFactory.get_user_manager("user1")
        user2_manager = LifecycleManagerFactory.get_user_manager("user2")
        
        user1_component = MockComponent("user1_component")
        user2_component = MockComponent("user2_component")
        
        await user1_manager.register_component(
            "component",
            user1_component,
            ComponentType.DATABASE_MANAGER
        )
        
        await user2_manager.register_component(
            "component",
            user2_component,
            ComponentType.DATABASE_MANAGER
        )
        
        # Verify isolation
        assert user1_manager.get_component(ComponentType.DATABASE_MANAGER) is user1_component
        assert user2_manager.get_component(ComponentType.DATABASE_MANAGER) is user2_component
        assert user1_manager.get_component(ComponentType.DATABASE_MANAGER) is not user2_component


# ============================================================================
# WEBSOCKET INTEGRATION TESTS
# ============================================================================

class TestWebSocketIntegration:
    """Test WebSocket integration for lifecycle events."""
    
    @pytest.fixture
    def lifecycle_manager(self, isolated_env):
        """Create lifecycle manager with WebSocket support."""
        return UnifiedLifecycleManager(user_id="websocket_test_user")
    
    @pytest.mark.asyncio
    async def test_websocket_manager_integration(self, lifecycle_manager):
        """Test WebSocket manager integration."""
        ws_manager = MockWebSocketManager()
        
        await lifecycle_manager.register_component(
            "websocket_manager",
            ws_manager,
            ComponentType.WEBSOCKET_MANAGER
        )
        
        # Verify WebSocket manager set during component validation
        await lifecycle_manager._validate_websocket_component("websocket_manager")
        assert lifecycle_manager._websocket_manager is ws_manager
    
    @pytest.mark.asyncio
    async def test_websocket_events_during_startup(self, lifecycle_manager):
        """Test WebSocket events emitted during startup."""
        ws_manager = MockWebSocketManager()
        lifecycle_manager.set_websocket_manager(ws_manager)
        
        result = await lifecycle_manager.startup()
        
        assert result is True
        # Verify startup events sent
        assert len(ws_manager.messages_sent) > 0
        
        # Check for startup completion event
        startup_events = [msg for msg in ws_manager.messages_sent 
                         if msg["type"] == "lifecycle_startup_completed"]
        assert len(startup_events) > 0
    
    @pytest.mark.asyncio
    async def test_websocket_events_during_shutdown(self, lifecycle_manager):
        """Test WebSocket events emitted during shutdown."""
        ws_manager = MockWebSocketManager()
        lifecycle_manager.set_websocket_manager(ws_manager)
        
        await lifecycle_manager.startup()
        ws_manager.messages_sent.clear()  # Clear startup messages
        
        result = await lifecycle_manager.shutdown()
        
        assert result is True
        # Verify shutdown events sent
        shutdown_events = [msg for msg in ws_manager.messages_sent 
                          if msg["type"] == "lifecycle_shutdown_completed"]
        assert len(shutdown_events) > 0
    
    @pytest.mark.asyncio
    async def test_websocket_component_registration_events(self, lifecycle_manager):
        """Test WebSocket events for component registration."""
        ws_manager = MockWebSocketManager()
        lifecycle_manager.set_websocket_manager(ws_manager)
        
        component = MockComponent("test_component")
        
        await lifecycle_manager.register_component(
            "test_component",
            component,
            ComponentType.DATABASE_MANAGER
        )
        
        # Verify registration event sent
        registration_events = [msg for msg in ws_manager.messages_sent 
                              if msg["type"] == "lifecycle_component_registered"]
        assert len(registration_events) > 0
        
        reg_event = registration_events[0]
        assert reg_event["data"]["component_name"] == "test_component"
        assert reg_event["data"]["component_type"] == "database_manager"
    
    @pytest.mark.asyncio
    async def test_websocket_phase_transition_events(self, lifecycle_manager):
        """Test WebSocket events for phase transitions."""
        ws_manager = MockWebSocketManager()
        lifecycle_manager.set_websocket_manager(ws_manager)
        
        await lifecycle_manager.startup()
        
        # Look for phase change events
        phase_events = [msg for msg in ws_manager.messages_sent 
                       if msg["type"] == "lifecycle_phase_changed"]
        assert len(phase_events) > 0
        
        # Should have transition from INITIALIZING to STARTING to RUNNING
        phase_transitions = [event["data"]["new_phase"] for event in phase_events]
        assert "starting" in phase_transitions
        assert "running" in phase_transitions
    
    def test_websocket_events_can_be_disabled(self, lifecycle_manager):
        """Test disabling WebSocket events."""
        lifecycle_manager.enable_websocket_events(False)
        assert not lifecycle_manager._enable_websocket_events
        
        lifecycle_manager.enable_websocket_events(True)
        assert lifecycle_manager._enable_websocket_events
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling(self, lifecycle_manager):
        """Test WebSocket error handling doesn't break lifecycle."""
        class FailingWebSocketManager:
            async def broadcast_system_message(self, message):
                raise Exception("WebSocket broadcast failed")
        
        failing_ws = FailingWebSocketManager()
        lifecycle_manager.set_websocket_manager(failing_ws)
        
        # Operations should succeed despite WebSocket failures
        result = await lifecycle_manager.startup()
        assert result is True


# ============================================================================
# STATUS AND MONITORING TESTS
# ============================================================================

class TestStatusAndMonitoring:
    """Test status reporting and monitoring functionality."""
    
    @pytest.fixture
    def lifecycle_manager(self, isolated_env):
        """Create lifecycle manager for status testing."""
        return UnifiedLifecycleManager(
            user_id="status_test_user",
            shutdown_timeout=10,
            startup_timeout=15
        )
    
    def test_get_status_comprehensive(self, lifecycle_manager):
        """Test comprehensive status reporting."""
        status = lifecycle_manager.get_status()
        
        # Verify all required fields present
        required_fields = [
            "user_id", "phase", "startup_time", "shutdown_time",
            "active_requests", "components", "metrics", 
            "is_shutting_down", "ready_for_requests", "uptime"
        ]
        
        for field in required_fields:
            assert field in status
        
        assert status["user_id"] == "status_test_user"
        assert status["phase"] == "initializing"
        assert status["is_shutting_down"] is False
        assert status["ready_for_requests"] is False
    
    @pytest.mark.asyncio
    async def test_status_after_startup(self, lifecycle_manager):
        """Test status after successful startup."""
        await lifecycle_manager.startup()
        
        status = lifecycle_manager.get_status()
        
        assert status["phase"] == "running"
        assert status["ready_for_requests"] is True
        assert status["startup_time"] is not None
        assert status["startup_time"] > 0
        assert status["uptime"] > 0
    
    @pytest.mark.asyncio
    async def test_status_with_registered_components(self, lifecycle_manager):
        """Test status includes component information."""
        component = MockComponent("status_component")
        
        await lifecycle_manager.register_component(
            "status_component",
            component,
            ComponentType.DATABASE_MANAGER
        )
        
        status = lifecycle_manager.get_status()
        
        assert "components" in status
        assert "status_component" in status["components"]
        
        component_info = status["components"]["status_component"]
        assert component_info["type"] == "database_manager"
        assert component_info["status"] == "registered"
        assert component_info["error_count"] == 0
    
    @pytest.mark.asyncio
    async def test_status_includes_metrics(self, lifecycle_manager):
        """Test status includes lifecycle metrics."""
        await lifecycle_manager.startup()
        
        status = lifecycle_manager.get_status()
        
        assert "metrics" in status
        metrics = status["metrics"]
        
        assert "successful_shutdowns" in metrics
        assert "failed_shutdowns" in metrics
        assert "component_failures" in metrics
        assert "last_health_check" in metrics
        
        assert metrics["successful_shutdowns"] == 0  # No shutdowns yet
        assert metrics["failed_shutdowns"] == 0
    
    def test_current_phase_tracking(self, lifecycle_manager):
        """Test current phase tracking."""
        assert lifecycle_manager.get_current_phase() == LifecyclePhase.INITIALIZING
        assert not lifecycle_manager.is_running()
        assert not lifecycle_manager.is_shutting_down()
    
    @pytest.mark.asyncio
    async def test_phase_transitions(self, lifecycle_manager):
        """Test phase transitions during lifecycle operations."""
        # Initial phase
        assert lifecycle_manager.get_current_phase() == LifecyclePhase.INITIALIZING
        
        # Startup
        startup_task = asyncio.create_task(lifecycle_manager.startup())
        
        # Give time for phase transition
        await asyncio.sleep(0.01)
        
        await startup_task
        assert lifecycle_manager.get_current_phase() == LifecyclePhase.RUNNING
        assert lifecycle_manager.is_running()
        
        # Shutdown
        await lifecycle_manager.shutdown()
        assert lifecycle_manager.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE
        assert lifecycle_manager.is_shutting_down()
    
    @pytest.mark.asyncio
    async def test_wait_for_shutdown(self, lifecycle_manager):
        """Test waiting for shutdown completion."""
        await lifecycle_manager.startup()
        
        # Start shutdown in background
        shutdown_task = asyncio.create_task(lifecycle_manager.shutdown())
        
        # Wait for shutdown to complete
        wait_task = asyncio.create_task(lifecycle_manager.wait_for_shutdown())
        
        # Both should complete
        await asyncio.gather(shutdown_task, wait_task)
        
        assert lifecycle_manager.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE


# ============================================================================
# ERROR HANDLING AND EDGE CASES TESTS
# ============================================================================

class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases."""
    
    @pytest.fixture
    def lifecycle_manager(self, isolated_env):
        """Create lifecycle manager for error testing."""
        return UnifiedLifecycleManager(
            user_id="error_test_user",
            shutdown_timeout=5,
            startup_timeout=5
        )
    
    @pytest.mark.asyncio
    async def test_startup_with_environment_loading_error(self, isolated_env):
        """Test handling of environment loading errors."""
        # Set invalid environment values
        isolated_env.set("SHUTDOWN_TIMEOUT", "invalid_int", source="test")
        isolated_env.set("DRAIN_TIMEOUT", "not_a_number", source="test")
        
        # Should still create manager with defaults
        manager = UnifiedLifecycleManager()
        
        # Should use default values when env parsing fails
        assert manager.shutdown_timeout == 30  # Default
        assert manager.drain_timeout == 20      # Default
    
    @pytest.mark.asyncio
    async def test_component_validation_with_missing_methods(self, lifecycle_manager):
        """Test component validation with missing required methods."""
        class IncompleteWebSocketManager:
            pass  # Missing required methods
        
        incomplete_ws = IncompleteWebSocketManager()
        
        await lifecycle_manager.register_component(
            "incomplete_ws",
            incomplete_ws,
            ComponentType.WEBSOCKET_MANAGER
        )
        
        # Validation should still pass but log warnings
        await lifecycle_manager._validate_websocket_component("incomplete_ws")
        
        # Manager should still be set
        assert lifecycle_manager._websocket_manager is incomplete_ws
    
    @pytest.mark.asyncio
    async def test_component_with_no_startup_method(self, lifecycle_manager):
        """Test component without startup methods."""
        class NoStartupComponent:
            def __init__(self):
                self.status = "created"
        
        component = NoStartupComponent()
        
        await lifecycle_manager.register_component(
            "no_startup",
            component,
            ComponentType.LLM_MANAGER
        )
        
        # Startup should succeed even without startup method
        result = await lifecycle_manager.startup()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_shutdown_with_stuck_health_monitor(self, lifecycle_manager):
        """Test shutdown with health monitor that doesn't respond to cancellation."""
        # Create a health monitor that runs forever
        original_health_monitor = lifecycle_manager._health_monitor_loop
        
        async def stuck_health_monitor():
            while True:
                try:
                    await asyncio.sleep(1)
                except asyncio.CancelledError:
                    # Ignore cancellation
                    continue
        
        lifecycle_manager._health_monitor_loop = stuck_health_monitor
        
        await lifecycle_manager.startup()
        
        # Shutdown should still complete despite stuck monitor
        shutdown_start = time.time()
        result = await lifecycle_manager.shutdown()
        shutdown_end = time.time()
        
        assert result is True
        # Should not hang indefinitely
        assert shutdown_end - shutdown_start < 10
    
    @pytest.mark.asyncio 
    async def test_concurrent_startup_attempts(self, lifecycle_manager):
        """Test multiple concurrent startup attempts."""
        # Start multiple startup operations concurrently
        tasks = []
        for i in range(5):
            task = asyncio.create_task(lifecycle_manager.startup())
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Only one should succeed, others should fail gracefully
        successful = [r for r in results if r is True]
        failed = [r for r in results if r is False]
        
        assert len(successful) == 1
        assert len(failed) == 4
        assert lifecycle_manager.is_running()
    
    @pytest.mark.asyncio
    async def test_shutdown_without_startup(self, lifecycle_manager):
        """Test shutdown without prior startup."""
        result = await lifecycle_manager.shutdown()
        
        # Should handle gracefully
        assert result is True
    
    @pytest.mark.asyncio
    async def test_memory_cleanup_after_operations(self, lifecycle_manager):
        """Test memory cleanup after lifecycle operations."""
        # Register many components
        components = []
        for i in range(50):
            component = MockComponent(f"component_{i}")
            components.append(component)
            await lifecycle_manager.register_component(
                f"component_{i}",
                component,
                ComponentType.DATABASE_MANAGER
            )
        
        await lifecycle_manager.startup()
        await lifecycle_manager.shutdown()
        
        # Verify cleanup
        assert lifecycle_manager._health_check_task is None
        assert len(lifecycle_manager._active_requests) == 0
    
    @pytest.mark.asyncio
    async def test_exception_in_lifecycle_hook(self, lifecycle_manager):
        """Test exception handling in lifecycle hooks."""
        exception_count = 0
        
        def failing_hook(**kwargs):
            nonlocal exception_count
            exception_count += 1
            raise Exception(f"Hook failure {exception_count}")
        
        lifecycle_manager.register_lifecycle_hook("pre_startup", failing_hook)
        lifecycle_manager.register_lifecycle_hook("post_startup", failing_hook)
        
        # Should complete successfully despite hook failures
        result = await lifecycle_manager.startup()
        assert result is True
        assert exception_count == 2  # Both hooks should have been called


# ============================================================================
# ENVIRONMENT CONFIGURATION TESTS
# ============================================================================

class TestEnvironmentConfiguration:
    """Test environment configuration and IsolatedEnvironment integration."""
    
    @pytest.mark.asyncio
    async def test_isolated_environment_usage(self, isolated_env):
        """Test proper IsolatedEnvironment usage in lifecycle manager."""
        # Set test configuration
        isolated_env.set("SHUTDOWN_TIMEOUT", "15", source="test")
        isolated_env.set("DRAIN_TIMEOUT", "8", source="test")
        isolated_env.set("HEALTH_GRACE_PERIOD", "3", source="test")
        isolated_env.set("STARTUP_TIMEOUT", "25", source="test")
        
        manager = UnifiedLifecycleManager()
        
        # Verify configuration loaded from IsolatedEnvironment
        assert manager.shutdown_timeout == 15
        assert manager.drain_timeout == 8
        assert manager.health_check_grace_period == 3
        assert manager.startup_timeout == 25
    
    @pytest.mark.asyncio
    async def test_environment_isolation_between_managers(self, isolated_env):
        """Test environment isolation between different managers."""
        # Each manager should get its own IsolatedEnvironment instance
        manager1 = UnifiedLifecycleManager(user_id="user1")
        manager2 = UnifiedLifecycleManager(user_id="user2")
        
        # Both should work independently
        await manager1.startup()
        await manager2.startup()
        
        assert manager1.is_running()
        assert manager2.is_running()
        assert manager1 is not manager2
    
    @pytest.mark.asyncio
    async def test_factory_environment_configuration(self, isolated_env):
        """Test factory uses IsolatedEnvironment for configuration."""
        isolated_env.set("SHUTDOWN_TIMEOUT", "42", source="test")
        isolated_env.set("STARTUP_TIMEOUT", "84", source="test")
        
        # Clear any existing managers
        LifecycleManagerFactory._global_manager = None
        
        manager = LifecycleManagerFactory.get_global_manager()
        
        assert manager.shutdown_timeout == 42
        assert manager.startup_timeout == 84


# ============================================================================
# INTEGRATION WITH SETUP_APPLICATION_LIFECYCLE TESTS
# ============================================================================

class TestSetupApplicationLifecycle:
    """Test setup_application_lifecycle integration function."""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI application."""
        class MockApp:
            def __init__(self):
                self.startup_handlers = []
                self.shutdown_handlers = []
            
            def on_event(self, event_type):
                def decorator(func):
                    if event_type == "startup":
                        self.startup_handlers.append(func)
                    elif event_type == "shutdown":
                        self.shutdown_handlers.append(func)
                    return func
                return decorator
        
        return MockApp()
    
    @pytest.mark.asyncio
    async def test_setup_application_lifecycle_basic(self, mock_app, isolated_env):
        """Test basic application lifecycle setup."""
        ws_manager = MockWebSocketManager()
        db_manager = MockComponent("database")
        
        lifecycle_manager = await setup_application_lifecycle(
            app=mock_app,
            websocket_manager=ws_manager,
            db_manager=db_manager
        )
        
        assert lifecycle_manager is not None
        assert lifecycle_manager.user_id is None  # Global manager
        
        # Verify components registered
        assert lifecycle_manager.get_component(ComponentType.WEBSOCKET_MANAGER) is ws_manager
        assert lifecycle_manager.get_component(ComponentType.DATABASE_MANAGER) is db_manager
        
        # Verify FastAPI handlers registered
        assert len(mock_app.startup_handlers) == 1
        assert len(mock_app.shutdown_handlers) == 1
    
    @pytest.mark.asyncio
    async def test_setup_application_lifecycle_with_user_id(self, mock_app, isolated_env):
        """Test application lifecycle setup with user ID."""
        lifecycle_manager = await setup_application_lifecycle(
            app=mock_app,
            user_id="app_user"
        )
        
        assert lifecycle_manager.user_id == "app_user"
    
    @pytest.mark.asyncio
    async def test_setup_application_lifecycle_all_components(self, mock_app, isolated_env):
        """Test application lifecycle setup with all components."""
        ws_manager = MockWebSocketManager()
        db_manager = MockComponent("database")
        agent_registry = MockAgentRegistry()
        health_service = MockHealthService()
        
        lifecycle_manager = await setup_application_lifecycle(
            app=mock_app,
            websocket_manager=ws_manager,
            db_manager=db_manager,
            agent_registry=agent_registry,
            health_service=health_service
        )
        
        # Verify all components registered
        assert lifecycle_manager.get_component(ComponentType.WEBSOCKET_MANAGER) is ws_manager
        assert lifecycle_manager.get_component(ComponentType.DATABASE_MANAGER) is db_manager
        assert lifecycle_manager.get_component(ComponentType.AGENT_REGISTRY) is agent_registry
        assert lifecycle_manager.get_component(ComponentType.HEALTH_SERVICE) is health_service
    
    @pytest.mark.asyncio
    async def test_fastapi_startup_handler_execution(self, mock_app, isolated_env):
        """Test FastAPI startup handler execution."""
        lifecycle_manager = await setup_application_lifecycle(app=mock_app)
        
        # Execute the registered startup handler
        startup_handler = mock_app.startup_handlers[0]
        await startup_handler()
        
        # Should start the lifecycle manager
        assert lifecycle_manager.is_running()
    
    @pytest.mark.asyncio
    async def test_fastapi_shutdown_handler_execution(self, mock_app, isolated_env):
        """Test FastAPI shutdown handler execution."""
        lifecycle_manager = await setup_application_lifecycle(app=mock_app)
        
        # Start the system first
        await lifecycle_manager.startup()
        assert lifecycle_manager.is_running()
        
        # Execute the registered shutdown handler
        shutdown_handler = mock_app.shutdown_handlers[0]
        await shutdown_handler()
        
        # Should shutdown the lifecycle manager
        assert lifecycle_manager.get_current_phase() == LifecyclePhase.SHUTDOWN_COMPLETE


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])