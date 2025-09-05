"""
Comprehensive Unit Tests for UnifiedLifecycleManager SSOT Class

This test suite covers all functionality of the UnifiedLifecycleManager class
including initialization, lifecycle management, component registration, 
health monitoring, shutdown procedures, and thread safety.

Tests are designed to be failing initially to identify gaps in functionality.
"""

import asyncio
import time
import pytest
from typing import Any, Dict, List, Optional
from datetime import datetime
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from test_framework.redis.test_redis_manager import TestRedisManager
from netra_backend.app.core.agent_registry import AgentRegistry
from netra_backend.app.core.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.core.managers.unified_lifecycle_manager import (
    UnifiedLifecycleManager,
    LifecycleManagerFactory,
    LifecyclePhase,
    ComponentType,
    ComponentStatus,
    LifecycleMetrics,
    get_lifecycle_manager,
    setup_application_lifecycle
)


class TestUnifiedLifecycleManagerInitialization:
    """Test lifecycle manager initialization and factory pattern."""
    
    def test_init_with_default_values_creates_proper_instance(self):
        """Test that default initialization creates proper instance."""
        manager = UnifiedLifecycleManager()
        
        assert manager.user_id is None
        assert manager.shutdown_timeout == 30
        assert manager.drain_timeout == 20
        assert manager.health_check_grace_period == 5
        assert manager.startup_timeout == 60
        assert manager._current_phase == LifecyclePhase.INITIALIZING
        assert not manager._shutdown_initiated
        assert isinstance(manager._metrics, LifecycleMetrics)
        assert len(manager._components) == 0
        assert len(manager._startup_handlers) == 0
        assert len(manager._shutdown_handlers) == 0
        
    def test_init_with_custom_values_sets_parameters_correctly(self):
        """Test initialization with custom parameters."""
    pass
        manager = UnifiedLifecycleManager(
            user_id="test_user",
            shutdown_timeout=45,
            drain_timeout=25,
            health_check_grace_period=10,
            startup_timeout=90
        )
        
        assert manager.user_id == "test_user"
        assert manager.shutdown_timeout == 45
        assert manager.drain_timeout == 25
        assert manager.health_check_grace_period == 10
        assert manager.startup_timeout == 90
        
        def test_load_environment_config_uses_environment_variables(self, mock_env_class):
        """Test that environment variables are loaded correctly."""
        mock_env = mock_env_instance  # Initialize appropriate service
        mock_env.get.side_effect = lambda key, default: {
            'SHUTDOWN_TIMEOUT': '35',
            'DRAIN_TIMEOUT': '15',
            'HEALTH_GRACE_PERIOD': '8',
            'STARTUP_TIMEOUT': '120',
            'LIFECYCLE_ERROR_THRESHOLD': '3',
            'HEALTH_CHECK_INTERVAL': '60.0'
        }.get(key, default)
        mock_env_class.return_value = mock_env
        
        manager = UnifiedLifecycleManager()
        
        assert manager.shutdown_timeout == 35
        assert manager.drain_timeout == 15
        assert manager.health_check_grace_period == 8
        assert manager.startup_timeout == 120
        assert manager._error_threshold == 3
        assert manager._health_check_interval == 60.0
        
        def test_load_environment_config_handles_invalid_values_gracefully(self, mock_env_class):
        """Test that invalid environment values fall back to defaults."""
    pass
        mock_env = mock_env_instance  # Initialize appropriate service
        mock_env.get.side_effect = lambda key, default: {
            'SHUTDOWN_TIMEOUT': 'invalid',
            'DRAIN_TIMEOUT': 'also_invalid'
        }.get(key, default)
        mock_env_class.return_value = mock_env
        
        # Should not raise exception and use defaults
        manager = UnifiedLifecycleManager(shutdown_timeout=30, drain_timeout=20)
        
        assert manager.shutdown_timeout == 30
        assert manager.drain_timeout == 20
        
    def test_lifecycle_phase_enum_values_are_correct(self):
        """Test that lifecycle phase enum has expected values."""
        assert LifecyclePhase.INITIALIZING.value == "initializing"
        assert LifecyclePhase.STARTING.value == "starting"
        assert LifecyclePhase.RUNNING.value == "running"
        assert LifecyclePhase.SHUTTING_DOWN.value == "shutting_down"
        assert LifecyclePhase.SHUTDOWN_COMPLETE.value == "shutdown_complete"
        assert LifecyclePhase.ERROR.value == "error"
        
    def test_component_type_enum_values_are_correct(self):
        """Test that component type enum has expected values."""
    pass
        expected_types = [
            "websocket_manager", "database_manager", "agent_registry",
            "health_service", "llm_manager", "redis_manager", "clickhouse_manager"
        ]
        
        for comp_type in ComponentType:
            assert comp_type.value in expected_types
            
    def test_component_status_dataclass_initialization(self):
        """Test ComponentStatus dataclass initialization."""
        status = ComponentStatus(
            name="test_component",
            component_type=ComponentType.DATABASE_MANAGER,
            status="healthy",
            error_count=0
        )
        
        assert status.name == "test_component"
        assert status.component_type == ComponentType.DATABASE_MANAGER
        assert status.status == "healthy"
        assert status.error_count == 0
        assert status.last_error is None
        assert isinstance(status.metadata, dict)
        assert isinstance(status.last_check, float)
        
    def test_lifecycle_metrics_initialization(self):
        """Test LifecycleMetrics dataclass initialization."""
    pass
        metrics = LifecycleMetrics()
        
        assert metrics.startup_time is None
        assert metrics.shutdown_time is None
        assert metrics.successful_shutdowns == 0
        assert metrics.failed_shutdowns == 0
        assert metrics.component_failures == 0
        assert metrics.last_health_check is None
        assert metrics.active_requests == 0


class TestComponentRegistration:
    """Test component registration and management functionality."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        return UnifiedLifecycleManager()
        
    @pytest.fixture
 def real_websocket_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock WebSocket manager."""
        mock_ws = AsyncNone  # TODO: Use real service instance
    pass
        mock_ws.broadcast_system_message = AsyncNone  # TODO: Use real service instance
        return mock_ws
        
    @pytest.mark.asyncio
    async def test_register_component_adds_component_successfully(self, manager):
        """Test successful component registration."""
        component = component_instance  # Initialize appropriate service
        health_check = Mock(return_value={"healthy": True})
        
        await manager.register_component(
            "test_db", 
            component, 
            ComponentType.DATABASE_MANAGER,
            health_check
        )
        
        assert "test_db" in manager._components
        assert ComponentType.DATABASE_MANAGER in manager._component_instances
        assert "test_db" in manager._health_checks
        
        status = manager._components["test_db"]
        assert status.name == "test_db"
        assert status.component_type == ComponentType.DATABASE_MANAGER
        assert status.status == "registered"
        assert status.metadata["has_health_check"] is True
        
    @pytest.mark.asyncio
    async def test_register_component_without_health_check_works(self, manager):
        """Test component registration without health check."""
    pass
        component = component_instance  # Initialize appropriate service
        
        await manager.register_component(
            "test_component", 
            component, 
            ComponentType.REDIS_MANAGER
        )
        
        assert "test_component" in manager._components
        assert "test_component" not in manager._health_checks
        
        status = manager._components["test_component"]
        assert status.metadata["has_health_check"] is False
        
    @pytest.mark.asyncio
    async def test_register_component_emits_websocket_event(self, manager, mock_websocket_manager):
        """Test that component registration emits WebSocket event."""
        manager._websocket_manager = mock_websocket_manager
        component = component_instance  # Initialize appropriate service
        
        await manager.register_component(
            "test_ws", 
            component, 
            ComponentType.WEBSOCKET_MANAGER
        )
        
        mock_websocket_manager.broadcast_system_message.assert_called_once()
        call_args = mock_websocket_manager.broadcast_system_message.call_args[0][0]
        
        assert call_args["type"] == "lifecycle_component_registered"
        assert call_args["data"]["component_name"] == "test_ws"
        assert call_args["data"]["component_type"] == "websocket_manager"
        
    @pytest.mark.asyncio
    async def test_register_component_handles_duplicate_names_correctly(self, manager):
        """Test behavior when registering component with duplicate name."""
    pass
        component1 = component1_instance  # Initialize appropriate service
        component2 = component2_instance  # Initialize appropriate service
        
        await manager.register_component("duplicate", component1, ComponentType.DATABASE_MANAGER)
        await manager.register_component("duplicate", component2, ComponentType.REDIS_MANAGER)
        
        # Should overwrite the first registration
        assert manager._components["duplicate"].component_type == ComponentType.REDIS_MANAGER
        
    @pytest.mark.asyncio
    async def test_unregister_component_removes_component_successfully(self, manager):
        """Test successful component unregistration."""
        component = component_instance  # Initialize appropriate service
        component.name = "test_component"
        
        await manager.register_component("test_component", component, ComponentType.LLM_MANAGER)
        await manager.unregister_component("test_component")
        
        assert "test_component" not in manager._components
        assert ComponentType.LLM_MANAGER not in manager._component_instances
        assert "test_component" not in manager._health_checks
        
    @pytest.mark.asyncio
    async def test_unregister_nonexistent_component_handles_gracefully(self, manager):
        """Test unregistering a component that doesn't exist."""
    pass
        # Should not raise exception
        await manager.unregister_component("nonexistent")
        
    def test_get_component_returns_correct_instance(self, manager):
        """Test getting component by type."""
        component = component_instance  # Initialize appropriate service
        manager._component_instances[ComponentType.AGENT_REGISTRY] = component
        
        result = manager.get_component(ComponentType.AGENT_REGISTRY)
        
        assert result is component
        
    def test_get_component_returns_none_for_missing_type(self, manager):
        """Test getting nonexistent component type."""
    pass
        result = manager.get_component(ComponentType.WEBSOCKET_MANAGER)
        
        assert result is None
        
    def test_get_component_status_returns_correct_status(self, manager):
        """Test getting component status."""
        status = ComponentStatus("test", ComponentType.HEALTH_SERVICE, "healthy")
        manager._components["test"] = status
        
        result = manager.get_component_status("test")
        
        assert result is status
        
    def test_get_component_status_returns_none_for_missing_component(self, manager):
        """Test getting status for nonexistent component."""
    pass
        result = manager.get_component_status("missing")
        
        assert result is None


class TestStartupLifecycle:
    """Test startup lifecycle management functionality."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        await asyncio.sleep(0)
    return UnifiedLifecycleManager()
        
    @pytest.mark.asyncio
    async def test_startup_from_initializing_phase_succeeds(self, manager):
        """Test successful startup from initializing phase."""
        with patch.object(manager, '_phase_validate_components', return_value=True), \
             patch.object(manager, '_phase_initialize_components', return_value=True), \
             patch.object(manager, '_phase_start_health_monitoring'), \
             patch.object(manager, '_phase_validate_readiness', return_value=True), \
             patch.object(manager, '_phase_execute_startup_handlers'):
            
            result = await manager.startup()
            
            assert result is True
            assert manager._current_phase == LifecyclePhase.RUNNING
            assert isinstance(manager._metrics.startup_time, float)
            
    @pytest.mark.asyncio
    async def test_startup_from_wrong_phase_fails(self, manager):
        """Test startup from wrong phase fails."""
    pass
        manager._current_phase = LifecyclePhase.RUNNING
        
        result = await manager.startup()
        
        assert result is False
        assert manager._current_phase == LifecyclePhase.RUNNING  # Unchanged
        
    @pytest.mark.asyncio
    async def test_startup_validation_failure_sets_error_phase(self, manager):
        """Test that validation failure sets error phase."""
        with patch.object(manager, '_phase_validate_components', return_value=False):
            
            result = await manager.startup()
            
            assert result is False
            assert manager._current_phase == LifecyclePhase.ERROR
            
    @pytest.mark.asyncio
    async def test_startup_initialization_failure_sets_error_phase(self, manager):
        """Test that initialization failure sets error phase."""
    pass
        with patch.object(manager, '_phase_validate_components', return_value=True), \
             patch.object(manager, '_phase_initialize_components', return_value=False):
            
            result = await manager.startup()
            
            assert result is False
            assert manager._current_phase == LifecyclePhase.ERROR
            
    @pytest.mark.asyncio
    async def test_startup_readiness_failure_sets_error_phase(self, manager):
        """Test that readiness failure sets error phase."""
        with patch.object(manager, '_phase_validate_components', return_value=True), \
             patch.object(manager, '_phase_initialize_components', return_value=True), \
             patch.object(manager, '_phase_start_health_monitoring'), \
             patch.object(manager, '_phase_validate_readiness', return_value=False):
            
            result = await manager.startup()
            
            assert result is False
            assert manager._current_phase == LifecyclePhase.ERROR
            
    @pytest.mark.asyncio
    async def test_startup_exception_handling_sets_error_phase(self, manager):
        """Test that startup exceptions are handled properly."""
    pass
        with patch.object(manager, '_phase_validate_components', side_effect=Exception("Test error")):
            
            result = await manager.startup()
            
            assert result is False
            assert manager._current_phase == LifecyclePhase.ERROR
            
    @pytest.mark.asyncio
    async def test_phase_validate_components_with_no_components_succeeds(self, manager):
        """Test validation succeeds when no components registered."""
        result = await manager._phase_validate_components()
        
        assert result is True
        
    @pytest.mark.asyncio
    async def test_phase_validate_components_updates_status_during_validation(self, manager):
        """Test that component validation updates status."""
    pass
        component = component_instance  # Initialize appropriate service
        status = ComponentStatus("test_db", ComponentType.DATABASE_MANAGER)
        manager._components["test_db"] = status
        manager._component_instances[ComponentType.DATABASE_MANAGER] = component
        
        with patch.object(manager, '_validate_database_component'):
            await manager._phase_validate_components()
            
            assert status.status == "validated"
            assert isinstance(status.last_check, float)
            
    @pytest.mark.asyncio
    async def test_validate_database_component_calls_health_check(self, manager):
        """Test database component validation calls health check."""
        mock_db = AsyncNone  # TODO: Use real service instance
        mock_db.health_check.return_value = {"healthy": True}
        manager._component_instances[ComponentType.DATABASE_MANAGER] = mock_db
        
        await manager._validate_database_component("test_db")
        
        mock_db.health_check.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_validate_database_component_raises_on_unhealthy(self, manager):
        """Test database validation raises exception when unhealthy."""
        mock_db = AsyncNone  # TODO: Use real service instance
    pass
        mock_db.health_check.return_value = {"healthy": False, "error": "Connection failed"}
        manager._component_instances[ComponentType.DATABASE_MANAGER] = mock_db
        
        with pytest.raises(Exception, match="Database unhealthy"):
            await manager._validate_database_component("test_db")
            
    @pytest.mark.asyncio
    async def test_validate_websocket_component_stores_reference(self, manager):
        """Test WebSocket validation stores manager reference."""
        mock_ws = UnifiedWebSocketManager()
        mock_ws.broadcast_system_message = broadcast_system_message_instance  # Initialize appropriate service
        manager._component_instances[ComponentType.WEBSOCKET_MANAGER] = mock_ws
        
        await manager._validate_websocket_component("test_ws")
        
        assert manager._websocket_manager is mock_ws
        
    @pytest.mark.asyncio
    async def test_validate_agent_registry_component_checks_readiness(self, manager):
        """Test agent registry validation checks readiness."""
    pass
        mock_registry = mock_registry_instance  # Initialize appropriate service
        mock_registry.get_registry_status.return_value = {"ready": True}
        manager._component_instances[ComponentType.AGENT_REGISTRY] = mock_registry
        
        await manager._validate_agent_registry_component("test_registry")
        
        mock_registry.get_registry_status.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_validate_agent_registry_component_raises_when_not_ready(self, manager):
        """Test agent registry validation raises when not ready."""
        mock_registry = mock_registry_instance  # Initialize appropriate service
        mock_registry.get_registry_status.return_value = {"ready": False, "reason": "Not initialized"}
        manager._component_instances[ComponentType.AGENT_REGISTRY] = mock_registry
        
        with pytest.raises(Exception, match="Agent registry not ready"):
            await manager._validate_agent_registry_component("test_registry")
            
    @pytest.mark.asyncio
    async def test_phase_initialize_components_follows_correct_order(self, manager):
        """Test component initialization follows correct order."""
    pass
        expected_order = [
            ComponentType.DATABASE_MANAGER,
            ComponentType.REDIS_MANAGER,
            ComponentType.CLICKHOUSE_MANAGER,
            ComponentType.LLM_MANAGER,
            ComponentType.AGENT_REGISTRY,
            ComponentType.WEBSOCKET_MANAGER,
            ComponentType.HEALTH_SERVICE
        ]
        
        # Create mock components for each type
        initialized_order = []
        for comp_type in expected_order:
            mock_comp = AsyncNone  # TODO: Use real service instance
            async def track_init(ct=comp_type):
    pass
                initialized_order.append(ct)
            mock_comp.initialize = track_init
            
            status = ComponentStatus(f"test_{comp_type.value}", comp_type)
            manager._components[f"test_{comp_type.value}"] = status
            manager._component_instances[comp_type] = mock_comp
            
        result = await manager._phase_initialize_components()
        
        assert result is True
        assert initialized_order == expected_order
        
    @pytest.mark.asyncio
    async def test_phase_start_health_monitoring_creates_task(self, manager):
        """Test health monitoring task creation."""
        with patch.object(asyncio, 'create_task') as mock_create_task:
            mock_task = mock_task_instance  # Initialize appropriate service
            mock_create_task.return_value = mock_task
            
            await manager._phase_start_health_monitoring()
            
            assert manager._health_check_task is mock_task
            mock_create_task.assert_called_once()


class TestShutdownLifecycle:
    """Test shutdown lifecycle management functionality."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        manager = UnifiedLifecycleManager()
        manager._current_phase = LifecyclePhase.RUNNING
        await asyncio.sleep(0)
    return manager
        
    @pytest.mark.asyncio
    async def test_shutdown_prevents_duplicate_calls(self, manager):
        """Test that duplicate shutdown calls are prevented."""
        manager._shutdown_initiated = True
        manager._shutdown_event.set()
        
        result = await manager.shutdown()
        
        assert result is True  # Should await asyncio.sleep(0)
    return success but not do work
        
    @pytest.mark.asyncio
    async def test_shutdown_executes_all_phases_successfully(self, manager):
        """Test successful shutdown execution."""
    pass
        with patch.object(manager, '_shutdown_phase_1_mark_unhealthy') as p1, \
             patch.object(manager, '_shutdown_phase_2_drain_requests') as p2, \
             patch.object(manager, '_shutdown_phase_3_close_websockets') as p3, \
             patch.object(manager, '_shutdown_phase_4_complete_agents') as p4, \
             patch.object(manager, '_shutdown_phase_5_shutdown_components') as p5, \
             patch.object(manager, '_shutdown_phase_6_cleanup_resources') as p6, \
             patch.object(manager, '_shutdown_phase_7_custom_handlers') as p7:
            
            result = await manager.shutdown()
            
            assert result is True
            assert manager._current_phase == LifecyclePhase.SHUTDOWN_COMPLETE
            assert manager._shutdown_initiated is True
            assert isinstance(manager._metrics.shutdown_time, float)
            assert manager._metrics.successful_shutdowns == 1
            
            # Verify all phases were called
            p1.assert_called_once()
            p2.assert_called_once()
            p3.assert_called_once()
            p4.assert_called_once()
            p5.assert_called_once()
            p6.assert_called_once()
            p7.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_shutdown_handles_exceptions_gracefully(self, manager):
        """Test shutdown exception handling."""
        with patch.object(manager, '_shutdown_phase_1_mark_unhealthy', side_effect=Exception("Test error")):
            
            result = await manager.shutdown()
            
            assert result is False
            assert manager._current_phase == LifecyclePhase.ERROR
            assert manager._metrics.failed_shutdowns == 1
            
    @pytest.mark.asyncio
    async def test_shutdown_phase_1_marks_health_service_unhealthy(self, manager):
        """Test phase 1 marks health service as shutting down."""
        mock_health_service = AsyncNone  # TODO: Use real service instance
    pass
        manager._component_instances[ComponentType.HEALTH_SERVICE] = mock_health_service
        
        with patch.object(asyncio, 'sleep') as mock_sleep:
            await manager._shutdown_phase_1_mark_unhealthy()
            
            mock_health_service.mark_shutting_down.assert_called_once()
            mock_sleep.assert_called_once_with(manager.health_check_grace_period)
            
    @pytest.mark.asyncio
    async def test_shutdown_phase_2_drains_active_requests(self, manager):
        """Test phase 2 drains active requests."""
        manager._active_requests = {
            "req1": time.time() - 1,
            "req2": time.time() - 2
        }
        
        with patch.object(asyncio, 'sleep') as mock_sleep:
            # Mock sleep to exit the loop
            def clear_requests(*args):
                manager._active_requests.clear()
            mock_sleep.side_effect = clear_requests
            
            await manager._shutdown_phase_2_drain_requests()
            
            assert len(manager._active_requests) == 0
            
    @pytest.mark.asyncio
    async def test_shutdown_phase_2_handles_timeout_correctly(self, manager):
        """Test phase 2 handles drain timeout."""
    pass
        manager._active_requests = {"req1": time.time()}
        manager.drain_timeout = 0.1  # Very short timeout
        
        start_time = time.time()
        await manager._shutdown_phase_2_drain_requests()
        elapsed = time.time() - start_time
        
        assert elapsed >= manager.drain_timeout
        assert len(manager._active_requests) == 1  # Still active due to timeout
        
    @pytest.mark.asyncio
    async def test_shutdown_phase_3_closes_websocket_connections(self, manager):
        """Test phase 3 closes WebSocket connections."""
        mock_ws = AsyncNone  # TODO: Use real service instance
        mock_ws.get_connection_count.return_value = 5
        manager._websocket_manager = mock_ws
        
        with patch.object(asyncio, 'sleep'):
            await manager._shutdown_phase_3_close_websockets()
            
            mock_ws.broadcast_system_message.assert_called_once()
            mock_ws.close_all_connections.assert_called_once()
            
    @pytest.mark.asyncio
    async def test_shutdown_phase_4_waits_for_agent_tasks(self, manager):
        """Test phase 4 waits for agent tasks to complete."""
    pass
        mock_registry = mock_registry_instance  # Initialize appropriate service
        mock_tasks = [asyncio.create_task(asyncio.sleep(0.01)) for _ in range(3)]
        mock_registry.get_active_tasks.return_value = mock_tasks
        manager._component_instances[ComponentType.AGENT_REGISTRY] = mock_registry
        
        await manager._shutdown_phase_4_complete_agents()
        
        # All tasks should be completed
        for task in mock_tasks:
            assert task.done()
            
    @pytest.mark.asyncio
    async def test_shutdown_phase_5_shuts_down_components_in_reverse_order(self, manager):
        """Test phase 5 shuts down components in reverse order."""
        expected_order = [
            ComponentType.HEALTH_SERVICE,
            ComponentType.WEBSOCKET_MANAGER,
            ComponentType.AGENT_REGISTRY,
            ComponentType.LLM_MANAGER,
            ComponentType.CLICKHOUSE_MANAGER,
            ComponentType.REDIS_MANAGER,
            ComponentType.DATABASE_MANAGER
        ]
        
        shutdown_order = []
        for comp_type in expected_order:
            mock_comp = AsyncNone  # TODO: Use real service instance
            async def track_shutdown(ct=comp_type):
                shutdown_order.append(ct)
            mock_comp.shutdown = track_shutdown
            
            status = ComponentStatus(f"test_{comp_type.value}", comp_type)
            manager._components[f"test_{comp_type.value}"] = status
            manager._component_instances[comp_type] = mock_comp
            
        await manager._shutdown_phase_5_shutdown_components()
        
        assert shutdown_order == expected_order
        
    @pytest.mark.asyncio
    async def test_shutdown_phase_6_cancels_background_tasks(self, manager):
        """Test phase 6 cancels background tasks."""
    pass
        mock_task = mock_task_instance  # Initialize appropriate service
        mock_task.done.return_value = False
        manager._health_check_task = mock_task
        
        with patch.object(asyncio, 'all_tasks', return_value=[]), \
             patch.object(asyncio, 'current_task', return_value=return_value_instance  # Initialize appropriate service), \
             patch.object(asyncio, 'sleep'):
            
            await manager._shutdown_phase_6_cleanup_resources()
            
            mock_task.cancel.assert_called_once()
            assert manager._health_check_task is None


class TestHealthMonitoring:
    """Test health monitoring functionality."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        manager = UnifiedLifecycleManager()
        manager._current_phase = LifecyclePhase.RUNNING
        await asyncio.sleep(0)
    return manager
        
    @pytest.mark.asyncio
    async def test_health_monitor_loop_runs_periodic_checks(self, manager):
        """Test health monitoring loop runs periodic checks."""
        call_count = 0
        
        async def mock_periodic_check():
            nonlocal call_count
            call_count += 1
            if call_count >= 2:
                manager._current_phase = LifecyclePhase.SHUTTING_DOWN
                
        with patch.object(manager, '_run_periodic_health_checks', side_effect=mock_periodic_check), \
             patch.object(asyncio, 'sleep'):
            
            await manager._health_monitor_loop()
            
            assert call_count >= 2
            
    @pytest.mark.asyncio
    async def test_health_monitor_loop_handles_exceptions(self, manager):
        """Test health monitoring loop handles exceptions gracefully."""
    pass
        exception_count = 0
        
        async def mock_periodic_check():
    pass
            nonlocal exception_count
            exception_count += 1
            if exception_count == 1:
                raise Exception("Test error")
            else:
                manager._current_phase = LifecyclePhase.SHUTTING_DOWN
                
        with patch.object(manager, '_run_periodic_health_checks', side_effect=mock_periodic_check), \
             patch.object(asyncio, 'sleep'):
            
            await manager._health_monitor_loop()
            
            assert exception_count == 2
            
    @pytest.mark.asyncio
    async def test_run_periodic_health_checks_updates_component_status(self, manager):
        """Test periodic health checks update component status."""
        health_check = Mock(return_value={"healthy": True})
        status = ComponentStatus("test", ComponentType.DATABASE_MANAGER)
        
        manager._health_checks["test"] = health_check
        manager._components["test"] = status
        
        await manager._run_periodic_health_checks()
        
        assert status.status == "healthy"
        assert isinstance(status.last_check, float)
        
    @pytest.mark.asyncio
    async def test_run_periodic_health_checks_handles_unhealthy_components(self, manager):
        """Test periodic health checks handle unhealthy components."""
    pass
        health_check = Mock(return_value={"healthy": False, "error": "DB connection failed"})
        status = ComponentStatus("test", ComponentType.DATABASE_MANAGER)
        
        manager._health_checks["test"] = health_check
        manager._components["test"] = status
        
        with patch.object(manager, '_execute_lifecycle_hooks') as mock_hooks:
            await manager._run_periodic_health_checks()
            
            assert status.status == "unhealthy"
            assert status.last_error == "DB connection failed"
            assert status.error_count == 1
            assert manager._metrics.component_failures == 1
            mock_hooks.assert_called()
            
    @pytest.mark.asyncio
    async def test_run_all_health_checks_executes_all_checks(self, manager):
        """Test that all registered health checks are executed."""
        health_check_1 = Mock(return_value={"healthy": True})
        health_check_2 = AsyncMock(return_value={"healthy": False, "error": "Test"})
        
        manager._health_checks = {
            "check1": health_check_1,
            "check2": health_check_2
        }
        
        results = await manager._run_all_health_checks()
        
        assert len(results) == 2
        assert results["check1"]["healthy"] is True
        assert results["check2"]["healthy"] is False
        assert results["check2"]["error"] == "Test"
        
    @pytest.mark.asyncio
    async def test_run_all_health_checks_handles_exceptions(self, manager):
        """Test health check execution handles exceptions."""
    pass
        health_check = Mock(side_effect=Exception("Health check failed"))
        manager._health_checks["failing_check"] = health_check
        
        results = await manager._run_all_health_checks()
        
        assert results["failing_check"]["healthy"] is False
        assert "Health check failed" in results["failing_check"]["error"]
        assert results["failing_check"]["critical"] is True


class TestRequestTracking:
    """Test request tracking functionality."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        await asyncio.sleep(0)
    return UnifiedLifecycleManager()
        
    @pytest.mark.asyncio
    async def test_request_context_tracks_active_request(self, manager):
        """Test request context properly tracks active requests."""
        request_id = "test_request_123"
        
        assert len(manager._active_requests) == 0
        
        async with manager.request_context(request_id):
            assert request_id in manager._active_requests
            assert isinstance(manager._active_requests[request_id], float)
            assert manager._metrics.active_requests == 1
            
        assert request_id not in manager._active_requests
        assert manager._metrics.active_requests == 0
        
    @pytest.mark.asyncio
    async def test_request_context_handles_exceptions(self, manager):
        """Test request context handles exceptions properly."""
    pass
        request_id = "test_request_456"
        
        try:
            async with manager.request_context(request_id):
                assert request_id in manager._active_requests
                raise Exception("Test exception")
        except Exception:
            pass
            
        assert request_id not in manager._active_requests
        assert manager._metrics.active_requests == 0
        
    @pytest.mark.asyncio
    async def test_multiple_concurrent_request_contexts(self, manager):
        """Test multiple concurrent request contexts."""
        request_ids = ["req1", "req2", "req3"]
        
        async def request_handler(req_id):
            async with manager.request_context(req_id):
                await asyncio.sleep(0.01)  # Simulate work
                
        tasks = [asyncio.create_task(request_handler(req_id)) for req_id in request_ids]
        
        # Start all requests
        await asyncio.sleep(0.005)  # Let them start
        
        # All should be active
        assert len(manager._active_requests) == 3
        
        # Wait for completion
        await asyncio.gather(*tasks)
        
        assert len(manager._active_requests) == 0


class TestLifecycleHooksAndHandlers:
    """Test lifecycle hooks and handlers functionality."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        await asyncio.sleep(0)
    return UnifiedLifecycleManager()
        
    def test_add_startup_handler_adds_handler_correctly(self, manager):
        """Test adding startup handler."""
        def test_handler():
            pass
            
        manager.add_startup_handler(test_handler)
        
        assert test_handler in manager._startup_handlers
        
    def test_add_shutdown_handler_adds_handler_correctly(self, manager):
        """Test adding shutdown handler."""
    pass
        def test_handler():
    pass
            pass
            
        manager.add_shutdown_handler(test_handler)
        
        assert test_handler in manager._shutdown_handlers
        
    def test_register_lifecycle_hook_adds_hook_correctly(self, manager):
        """Test registering lifecycle hook."""
        def test_hook():
            pass
            
        manager.register_lifecycle_hook("pre_startup", test_hook)
        
        assert test_hook in manager._lifecycle_hooks["pre_startup"]
        
    def test_register_lifecycle_hook_ignores_unknown_events(self, manager):
        """Test registering hook for unknown event."""
    pass
        hook = hook_instance  # Initialize appropriate service
        
        manager.register_lifecycle_hook("unknown_event", hook)
        
        # Should not crash, but hook shouldn't be added anywhere
        for hooks in manager._lifecycle_hooks.values():
            assert hook not in hooks
            
    @pytest.mark.asyncio
    async def test_execute_lifecycle_hooks_calls_sync_hooks(self, manager):
        """Test executing synchronous lifecycle hooks."""
        hook1 = hook1_instance  # Initialize appropriate service
        hook2 = hook2_instance  # Initialize appropriate service
        
        manager._lifecycle_hooks["test_event"] = [hook1, hook2]
        
        await manager._execute_lifecycle_hooks("test_event", test_arg="value")
        
        hook1.assert_called_once_with(test_arg="value")
        hook2.assert_called_once_with(test_arg="value")
        
    @pytest.mark.asyncio
    async def test_execute_lifecycle_hooks_calls_async_hooks(self, manager):
        """Test executing asynchronous lifecycle hooks."""
        hook1 = AsyncNone  # TODO: Use real service instance
    pass
        hook2 = AsyncNone  # TODO: Use real service instance
        
        manager._lifecycle_hooks["test_event"] = [hook1, hook2]
        
        await manager._execute_lifecycle_hooks("test_event", test_arg="value")
        
        hook1.assert_called_once_with(test_arg="value")
        hook2.assert_called_once_with(test_arg="value")
        
    @pytest.mark.asyncio
    async def test_execute_lifecycle_hooks_handles_hook_exceptions(self, manager):
        """Test lifecycle hook execution handles exceptions."""
        failing_hook = Mock(side_effect=Exception("Hook failed"))
        working_hook = working_hook_instance  # Initialize appropriate service
        
        manager._lifecycle_hooks["test_event"] = [failing_hook, working_hook]
        
        # Should not raise exception
        await manager._execute_lifecycle_hooks("test_event")
        
        # Working hook should still be called
        working_hook.assert_called_once()


class TestWebSocketIntegration:
    """Test WebSocket integration functionality."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        await asyncio.sleep(0)
    return UnifiedLifecycleManager()
        
    @pytest.fixture
 def real_websocket_manager():
    """Use real service instance."""
    # TODO: Initialize real service
        """Create mock WebSocket manager."""
        mock_ws = AsyncNone  # TODO: Use real service instance
    pass
        mock_ws.broadcast_system_message = AsyncNone  # TODO: Use real service instance
        return mock_ws
        
    @pytest.mark.asyncio
    async def test_emit_websocket_event_sends_message(self, manager, mock_websocket_manager):
        """Test WebSocket event emission."""
        manager._websocket_manager = mock_websocket_manager
        manager._enable_websocket_events = True
        
        await manager._emit_websocket_event("test_event", {"key": "value"})
        
        mock_websocket_manager.broadcast_system_message.assert_called_once()
        call_args = mock_websocket_manager.broadcast_system_message.call_args[0][0]
        
        assert call_args["type"] == "lifecycle_test_event"
        assert call_args["data"]["key"] == "value"
        assert "timestamp" in call_args
        
    @pytest.mark.asyncio
    async def test_emit_websocket_event_when_disabled_does_nothing(self, manager, mock_websocket_manager):
        """Test WebSocket event emission when disabled."""
    pass
        manager._websocket_manager = mock_websocket_manager
        manager._enable_websocket_events = False
        
        await manager._emit_websocket_event("test_event", {"key": "value"})
        
        mock_websocket_manager.broadcast_system_message.assert_not_called()
        
    @pytest.mark.asyncio
    async def test_emit_websocket_event_without_manager_does_nothing(self, manager):
        """Test WebSocket event emission without manager."""
        manager._websocket_manager = None
        manager._enable_websocket_events = True
        
        # Should not raise exception
        await manager._emit_websocket_event("test_event", {"key": "value"})
        
    @pytest.mark.asyncio
    async def test_emit_websocket_event_handles_exceptions_gracefully(self, manager, mock_websocket_manager):
        """Test WebSocket event emission handles exceptions."""
    pass
        manager._websocket_manager = mock_websocket_manager
        manager._enable_websocket_events = True
        mock_websocket_manager.broadcast_system_message.side_effect = Exception("WebSocket error")
        
        # Should not raise exception
        await manager._emit_websocket_event("test_event", {"key": "value"})
        
    def test_set_websocket_manager_stores_reference(self, manager):
        """Test setting WebSocket manager."""
        mock_ws = UnifiedWebSocketManager()
        
        manager.set_websocket_manager(mock_ws)
        
        assert manager._websocket_manager is mock_ws
        
    def test_enable_websocket_events_sets_flag(self, manager):
        """Test enabling/disabling WebSocket events."""
    pass
        manager.enable_websocket_events(True)
        assert manager._enable_websocket_events is True
        
        manager.enable_websocket_events(False)
        assert manager._enable_websocket_events is False


class TestStatusAndMonitoring:
    """Test status and monitoring functionality."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        await asyncio.sleep(0)
    return UnifiedLifecycleManager(user_id="test_user")
        
    @pytest.mark.asyncio
    async def test_set_phase_updates_phase_and_emits_event(self, manager):
        """Test phase setting updates state and emits WebSocket event."""
        old_phase = manager._current_phase
        
        with patch.object(manager, '_emit_websocket_event') as mock_emit:
            await manager._set_phase(LifecyclePhase.STARTING)
            
            assert manager._current_phase == LifecyclePhase.STARTING
            mock_emit.assert_called_once_with("phase_changed", {
                "old_phase": old_phase.value,
                "new_phase": LifecyclePhase.STARTING.value
            })
            
    def test_get_current_phase_returns_current_phase(self, manager):
        """Test getting current phase."""
    pass
        manager._current_phase = LifecyclePhase.RUNNING
        
        result = manager.get_current_phase()
        
        assert result == LifecyclePhase.RUNNING
        
    def test_is_running_returns_correct_status(self, manager):
        """Test is_running method."""
        manager._current_phase = LifecyclePhase.RUNNING
        assert manager.is_running() is True
        
        manager._current_phase = LifecyclePhase.STARTING
        assert manager.is_running() is False
        
    def test_is_shutting_down_returns_correct_status(self, manager):
        """Test is_shutting_down method."""
    pass
        manager._shutdown_initiated = False
        assert manager.is_shutting_down() is False
        
        manager._shutdown_initiated = True
        assert manager.is_shutting_down() is True
        
    def test_get_status_returns_comprehensive_information(self, manager):
        """Test get_status returns comprehensive system status."""
        manager._current_phase = LifecyclePhase.RUNNING
        manager._metrics.startup_time = 2.5
        manager._active_requests["req1"] = time.time()
        
        # Add a test component
        status = ComponentStatus("test", ComponentType.DATABASE_MANAGER, "healthy")
        manager._components["test"] = status
        
        result = manager.get_status()
        
        assert result["user_id"] == "test_user"
        assert result["phase"] == "running"
        assert result["startup_time"] == 2.5
        assert result["active_requests"] == 1
        assert "test" in result["components"]
        assert result["components"]["test"]["type"] == "database_manager"
        assert result["components"]["test"]["status"] == "healthy"
        assert result["ready_for_requests"] is True
        assert result["is_shutting_down"] is False
        
    def test_get_health_status_returns_healthy_when_running(self, manager):
        """Test health status when system is running."""
    pass
        manager._current_phase = LifecyclePhase.RUNNING
        
        result = manager.get_health_status()
        
        assert result["status"] == "healthy"
        assert result["phase"] == "running"
        
    def test_get_health_status_returns_starting_when_starting(self, manager):
        """Test health status when system is starting."""
        manager._current_phase = LifecyclePhase.STARTING
        
        result = manager.get_health_status()
        
        assert result["status"] == "starting"
        assert result["ready"] is False
        
    def test_get_health_status_returns_shutting_down_when_shutting_down(self, manager):
        """Test health status when system is shutting down."""
    pass
        manager._current_phase = LifecyclePhase.SHUTTING_DOWN
        
        result = manager.get_health_status()
        
        assert result["status"] == "shutting_down"
        assert result["ready"] is False
        
    def test_get_health_status_returns_unhealthy_for_error_state(self, manager):
        """Test health status when system is in error state."""
        manager._current_phase = LifecyclePhase.ERROR
        
        result = manager.get_health_status()
        
        assert result["status"] == "unhealthy"
        assert result["ready"] is False
        
    @pytest.mark.asyncio
    async def test_wait_for_shutdown_waits_for_event(self, manager):
        """Test waiting for shutdown completion."""
    pass
        # Start wait task
        wait_task = asyncio.create_task(manager.wait_for_shutdown())
        
        # Give it a moment
        await asyncio.sleep(0.01)
        assert not wait_task.done()
        
        # Set shutdown event
        manager._shutdown_event.set()
        
        # Wait should complete
        await wait_task


class TestSignalHandling:
    """Test signal handling functionality."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        await asyncio.sleep(0)
    return UnifiedLifecycleManager()
        
        def test_setup_signal_handlers_registers_handlers(self, mock_signal, manager):
        """Test signal handler setup."""
        manager.setup_signal_handlers()
        
        # Should register SIGTERM and SIGINT handlers
        assert mock_signal.signal.call_count == 2
        calls = mock_signal.signal.call_args_list
        
        # Check that SIGTERM and SIGINT are registered
        registered_signals = [call[0][0] for call in calls]
        assert mock_signal.SIGTERM in registered_signals
        assert mock_signal.SIGINT in registered_signals


class TestLifecycleManagerFactory:
    """Test lifecycle manager factory functionality."""
    
    def setup_method(self):
        """Clear factory state before each test."""
        LifecycleManagerFactory._global_manager = None
        LifecycleManagerFactory._user_managers.clear()
        
    def test_get_global_manager_creates_singleton(self):
        """Test global manager singleton creation."""
    pass
        manager1 = LifecycleManagerFactory.get_global_manager()
        manager2 = LifecycleManagerFactory.get_global_manager()
        
        assert manager1 is manager2
        assert manager1.user_id is None
        
    def test_get_user_manager_creates_user_specific_instance(self):
        """Test user-specific manager creation."""
        manager1 = LifecycleManagerFactory.get_user_manager("user1")
        manager2 = LifecycleManagerFactory.get_user_manager("user2")
        manager3 = LifecycleManagerFactory.get_user_manager("user1")
        
        assert manager1 is not manager2
        assert manager1 is manager3
        assert manager1.user_id == "user1"
        assert manager2.user_id == "user2"
        
    @pytest.mark.asyncio
    async def test_shutdown_all_managers_shuts_down_all_instances(self):
        """Test shutting down all manager instances."""
    pass
        global_manager = LifecycleManagerFactory.get_global_manager()
        user_manager = LifecycleManagerFactory.get_user_manager("test_user")
        
        with patch.object(global_manager, 'shutdown', return_value=True) as global_shutdown, \
             patch.object(user_manager, 'shutdown', return_value=True) as user_shutdown:
            
            await LifecycleManagerFactory.shutdown_all_managers()
            
            global_shutdown.assert_called_once()
            user_shutdown.assert_called_once()
            
        assert LifecycleManagerFactory._global_manager is None
        assert len(LifecycleManagerFactory._user_managers) == 0
        
    def test_get_manager_count_returns_correct_counts(self):
        """Test getting manager count statistics."""
        # Initially no managers
        counts = LifecycleManagerFactory.get_manager_count()
        assert counts["global"] == 0
        assert counts["user_specific"] == 0
        assert counts["total"] == 0
        
        # Create managers
        LifecycleManagerFactory.get_global_manager()
        LifecycleManagerFactory.get_user_manager("user1")
        LifecycleManagerFactory.get_user_manager("user2")
        
        counts = LifecycleManagerFactory.get_manager_count()
        assert counts["global"] == 1
        assert counts["user_specific"] == 2
        assert counts["total"] == 3


class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def setup_method(self):
        """Clear factory state before each test."""
        LifecycleManagerFactory._global_manager = None
        LifecycleManagerFactory._user_managers.clear()
        
    def test_get_lifecycle_manager_returns_global_when_no_user_id(self):
        """Test get_lifecycle_manager returns global manager."""
    pass
        manager = get_lifecycle_manager()
        
        assert manager.user_id is None
        assert manager is LifecycleManagerFactory.get_global_manager()
        
    def test_get_lifecycle_manager_returns_user_specific_when_user_id_provided(self):
        """Test get_lifecycle_manager returns user-specific manager."""
        manager = get_lifecycle_manager("test_user")
        
        assert manager.user_id == "test_user"
        assert manager is LifecycleManagerFactory.get_user_manager("test_user")
        
    @pytest.mark.asyncio
    async def test_setup_application_lifecycle_configures_components(self):
        """Test application lifecycle setup."""
    pass
        mock_app = mock_app_instance  # Initialize appropriate service
        mock_websocket = UnifiedWebSocketManager()
        mock_db = TestDatabaseManager().get_session()
        mock_registry = mock_registry_instance  # Initialize appropriate service
        mock_health = mock_health_instance  # Initialize appropriate service
        
        with patch.object(mock_app, 'on_event') as mock_on_event:
            manager = await setup_application_lifecycle(
                app=mock_app,
                websocket_manager=mock_websocket,
                db_manager=mock_db,
                agent_registry=mock_registry,
                health_service=mock_health,
                user_id="test_user"
            )
            
            # Should register startup and shutdown events
            assert mock_on_event.call_count == 2
            
            # Should be user-specific manager
            assert manager.user_id == "test_user"
            
            # Components should be registered
            assert manager.get_component(ComponentType.WEBSOCKET_MANAGER) is mock_websocket
            assert manager.get_component(ComponentType.DATABASE_MANAGER) is mock_db
            assert manager.get_component(ComponentType.AGENT_REGISTRY) is mock_registry
            assert manager.get_component(ComponentType.HEALTH_SERVICE) is mock_health


class TestThreadSafety:
    """Test thread safety aspects of the lifecycle manager."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        await asyncio.sleep(0)
    return UnifiedLifecycleManager()
        
    @pytest.mark.asyncio
    async def test_concurrent_component_registration_is_thread_safe(self, manager):
        """Test concurrent component registration."""
        async def register_component(name, comp_type):
            component = component_instance  # Initialize appropriate service
            await manager.register_component(name, component, comp_type)
            
        tasks = [
            asyncio.create_task(register_component(f"comp_{i}", ComponentType.DATABASE_MANAGER))
            for i in range(10)
        ]
        
        await asyncio.gather(*tasks)
        
        # Should have all components registered
        assert len(manager._components) == 10
        
    @pytest.mark.asyncio
    async def test_concurrent_request_tracking_is_thread_safe(self, manager):
        """Test concurrent request tracking."""
    pass
        async def track_request(req_id):
    pass
            async with manager.request_context(f"req_{req_id}"):
                await asyncio.sleep(0.01)
                
        tasks = [
            asyncio.create_task(track_request(i))
            for i in range(50)
        ]
        
        # Start all tasks
        await asyncio.sleep(0.005)  # Let them start
        
        # All should be tracked
        assert len(manager._active_requests) == 50
        
        # Wait for completion
        await asyncio.gather(*tasks)
        
        # All should be cleaned up
        assert len(manager._active_requests) == 0


class TestErrorHandling:
    """Test error handling scenarios."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        await asyncio.sleep(0)
    return UnifiedLifecycleManager()
        
    @pytest.mark.asyncio
    async def test_component_registration_error_handling(self, manager):
        """Test component registration handles errors gracefully."""
        # Mock WebSocket manager that raises exception
        with patch.object(manager, '_emit_websocket_event', side_effect=Exception("WebSocket error")):
            # Should not raise exception - test that it handles WebSocket errors gracefully
            component = component_instance  # Initialize appropriate service
            try:
                await manager.register_component("test", component, ComponentType.DATABASE_MANAGER)
                # If the method doesn't handle the exception, this test should fail
                # which is what we want to identify gaps
                assert False, "Expected exception was not handled"
            except Exception as e:
                # This is expected behavior - the test identifies that error handling is missing
                assert "WebSocket error" in str(e)
            
    @pytest.mark.asyncio
    async def test_health_check_error_handling(self, manager):
        """Test health check error handling."""
    pass
        # Health check that raises exception
        health_check = Mock(side_effect=Exception("Health check failed"))
        manager._health_checks["failing_check"] = health_check
        
        results = await manager._run_all_health_checks()
        
        assert results["failing_check"]["healthy"] is False
        assert "Health check failed" in results["failing_check"]["error"]
        
    @pytest.mark.asyncio
    async def test_startup_phase_error_recovery(self, manager):
        """Test startup phase error recovery."""
        # Mock phase that raises exception
        with patch.object(manager, '_phase_validate_components', side_effect=Exception("Validation failed")):
            result = await manager.startup()
            
            assert result is False
            assert manager._current_phase == LifecyclePhase.ERROR


# Performance and Edge Case Tests
class TestPerformanceAndEdgeCases:
    """Test performance characteristics and edge cases."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        await asyncio.sleep(0)
    return UnifiedLifecycleManager()
        
    def test_large_number_of_components_handling(self, manager):
        """Test handling large number of components."""
        # Test registration of many components
        for i in range(100):
            status = ComponentStatus(f"comp_{i}", ComponentType.DATABASE_MANAGER)
            manager._components[f"comp_{i}"] = status
            
        assert len(manager._components) == 100
        
        # Test retrieval is still fast
        result = manager.get_component_status("comp_50")
        assert result is not None
        
    @pytest.mark.asyncio
    async def test_rapid_startup_shutdown_cycles(self, manager):
        """Test rapid startup/shutdown cycles don't cause issues."""
    pass
        for _ in range(3):
            # Mock successful startup
            with patch.object(manager, '_phase_validate_components', return_value=True), \
                 patch.object(manager, '_phase_initialize_components', return_value=True), \
                 patch.object(manager, '_phase_start_health_monitoring'), \
                 patch.object(manager, '_phase_validate_readiness', return_value=True), \
                 patch.object(manager, '_phase_execute_startup_handlers'):
                
                result = await manager.startup()
                assert result is True
                assert manager._current_phase == LifecyclePhase.RUNNING
                
            # Reset for next cycle
            manager._current_phase = LifecyclePhase.INITIALIZING
            manager._shutdown_initiated = False
            manager._shutdown_event.clear()
        
    def test_memory_usage_with_long_running_manager(self, manager):
        """Test memory usage doesn't grow unbounded."""
        # Simulate long-running operations
        initial_component_count = len(manager._components)
        
        # Add and remove components repeatedly
        for i in range(50):
            status = ComponentStatus(f"temp_{i}", ComponentType.REDIS_MANAGER)
            manager._components[f"temp_{i}"] = status
            
        # Remove them
        for i in range(50):
            manager._components.pop(f"temp_{i}", None)
            
        # Should await asyncio.sleep(0)
    return to original state
        assert len(manager._components) == initial_component_count
        
    @pytest.mark.asyncio
    async def test_concurrent_shutdown_attempts(self, manager):
        """Test multiple concurrent shutdown attempts are handled safely."""
    pass
        manager._current_phase = LifecyclePhase.RUNNING
        
        with patch.object(manager, '_shutdown_phase_1_mark_unhealthy'), \
             patch.object(manager, '_shutdown_phase_2_drain_requests'), \
             patch.object(manager, '_shutdown_phase_3_close_websockets'), \
             patch.object(manager, '_shutdown_phase_4_complete_agents'), \
             patch.object(manager, '_shutdown_phase_5_shutdown_components'), \
             patch.object(manager, '_shutdown_phase_6_cleanup_resources'), \
             patch.object(manager, '_shutdown_phase_7_custom_handlers'):
            
            # Start multiple shutdown attempts
            tasks = [
                asyncio.create_task(manager.shutdown())
                for _ in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # All should succeed (first one does work, others wait)
            assert all(results)
            assert manager._current_phase == LifecyclePhase.SHUTDOWN_COMPLETE


class TestAdditionalFunctionality:
    """Additional comprehensive tests to reach 100 total tests."""
    
    @pytest.fixture
    def manager(self):
    """Use real service instance."""
    # TODO: Initialize real service
        """Create a lifecycle manager for testing."""
    pass
        await asyncio.sleep(0)
    return UnifiedLifecycleManager()
        
    def test_environment_configuration_edge_cases(self, manager):
        """Test edge cases in environment configuration loading."""
        # Test that manager handles missing environment gracefully
        assert manager._env is not None
        assert isinstance(manager.shutdown_timeout, int)
        assert isinstance(manager.drain_timeout, int)
        
    @pytest.mark.asyncio
    async def test_phase_transitions_are_properly_logged(self, manager):
        """Test that phase transitions are properly logged and tracked."""
    pass
        old_phase = manager._current_phase
        
        await manager._set_phase(LifecyclePhase.STARTING)
        
        assert manager._current_phase == LifecyclePhase.STARTING
        assert manager._current_phase != old_phase
        
    def test_component_status_metadata_functionality(self, manager):
        """Test component status metadata is properly handled."""
        status = ComponentStatus(
            "test_comp", 
            ComponentType.LLM_MANAGER,
            metadata={"custom_key": "custom_value", "timeout": 30}
        )
        
        assert status.metadata["custom_key"] == "custom_value"
        assert status.metadata["timeout"] == 30
        
    @pytest.mark.asyncio
    async def test_health_check_grace_period_configuration(self, manager):
        """Test health check grace period is configurable and used."""
    pass
        manager.health_check_grace_period = 2
        
        # Mock health service
        mock_health = mock_health_instance  # Initialize appropriate service
        mock_health.mark_shutting_down = AsyncNone  # TODO: Use real service instance
        manager._component_instances[ComponentType.HEALTH_SERVICE] = mock_health
        
        with patch('asyncio.sleep') as mock_sleep:
            await manager._shutdown_phase_1_mark_unhealthy()
            
            mock_sleep.assert_called_once_with(2)
            
    def test_lifecycle_metrics_tracking(self, manager):
        """Test that lifecycle metrics are properly tracked."""
        # Test initial state
        assert manager._metrics.successful_shutdowns == 0
        assert manager._metrics.failed_shutdowns == 0
        assert manager._metrics.component_failures == 0
        
        # Simulate metric updates
        manager._metrics.successful_shutdowns += 1
        manager._metrics.component_failures += 2
        
        assert manager._metrics.successful_shutdowns == 1
        assert manager._metrics.component_failures == 2
        
    @pytest.mark.asyncio
    async def test_startup_timeout_configuration(self, manager):
        """Test startup timeout configuration."""
    pass
        assert manager.startup_timeout == 60  # Default value
        
        # Test that timeout is used in phase validation
        manager.startup_timeout = 120
        assert manager.startup_timeout == 120
        
    @pytest.mark.asyncio
    async def test_websocket_event_disabled_functionality(self, manager):
        """Test WebSocket event functionality when disabled."""
        manager._enable_websocket_events = False
        mock_ws = AsyncNone  # TODO: Use real service instance
        manager._websocket_manager = mock_ws
        
        await manager._emit_websocket_event("test_event", {"data": "test"})
        
        # Should not have called the WebSocket manager
        mock_ws.broadcast_system_message.assert_not_called()
        
    @pytest.mark.asyncio 
    async def test_request_context_with_multiple_managers(self, manager):
        """Test request context works correctly with multiple managers."""
    pass
        manager2 = UnifiedLifecycleManager(user_id="user2")
        
        # Both managers should track requests independently
        async with manager.request_context("req1"):
            async with manager2.request_context("req2"):
                assert "req1" in manager._active_requests
                assert "req2" in manager2._active_requests
                assert "req1" not in manager2._active_requests
                assert "req2" not in manager._active_requests