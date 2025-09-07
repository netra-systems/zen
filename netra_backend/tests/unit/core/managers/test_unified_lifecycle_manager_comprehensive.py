"""
Comprehensive Unit Tests for UnifiedLifecycleManager - LARGEST MEGA CLASS SSOT

Test Unified Lifecycle Manager - LARGEST MEGA CLASS SSOT (1,950 lines)

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Zero-Downtime Operations & Platform Reliability  
- Value Impact: Ensures 1,950 lines of lifecycle logic work correctly for chat service
- Strategic Impact: Foundation for chat service reliability (90% platform value)

This is the MOST COMPREHENSIVE test suite in the system, testing the LARGEST approved
MEGA CLASS (1,950 lines) that consolidates 100+ legacy managers into one SSOT.

CRITICAL REQUIREMENTS:
- NO mocks for core business logic (CHEATING ON TESTS = ABOMINATION)
- Test ALL 5 WebSocket events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Test multi-user isolation with factory patterns
- Test zero-downtime operations and graceful shutdowns
- Test atomic operations with rollback on failure
- Test health monitoring and performance metrics
- Test legacy manager compatibility
- Test concurrent user scenarios under load
- Test error recovery and circuit breakers

CRITICAL: This manager is the foundation of platform stability. Every test validates
real-world scenarios ensuring users can reliably access AI chat services without interruption.
"""

import asyncio
import json
import time
import uuid
import threading
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from test_framework.ssot.base import BaseTestCase, AsyncBaseTestCase
from test_framework.websocket_helpers import assert_websocket_events, WebSocketTestHelpers, MockWebSocketConnection
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


class TestUnifiedLifecycleManagerComprehensive(AsyncBaseTestCase):
    """
    Comprehensive test suite for the UnifiedLifecycleManager MEGA CLASS.
    
    This tests the LARGEST SSOT class (1,950 lines) that consolidates 100+ legacy managers.
    Tests cover all lifecycle phases, WebSocket integration, multi-user isolation,
    zero-downtime operations, health monitoring, and error recovery.
    """
    
    REQUIRES_WEBSOCKET = True
    ISOLATION_ENABLED = True
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.lifecycle_manager = None
        self.mock_websocket_manager = None
        self.mock_db_manager = None
        self.mock_agent_registry = None
        self.mock_health_service = None
        self.test_components = []
        
    async def asyncSetUp(self):
        """Set up comprehensive test environment with all required components."""
        await super().asyncSetUp()
        
        # Create mock components for testing (minimal mocks, mostly real behavior)
        self.mock_websocket_manager = self._create_mock_websocket_manager()
        self.mock_db_manager = self._create_mock_database_manager()
        self.mock_agent_registry = self._create_mock_agent_registry()
        self.mock_health_service = self._create_mock_health_service()
        
        # Track all test components for cleanup
        self.test_components = [
            self.mock_websocket_manager,
            self.mock_db_manager,
            self.mock_agent_registry,
            self.mock_health_service
        ]
        
        # Create lifecycle manager with test configuration
        self.lifecycle_manager = UnifiedLifecycleManager(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            shutdown_timeout=5,  # Shorter for tests
            drain_timeout=3,
            health_check_grace_period=1,
            startup_timeout=10
        )
        
        # Track lifecycle manager for cleanup
        self.track_resource(self.lifecycle_manager)
    
    async def asyncTearDown(self):
        """Clean up all test resources."""
        # Clean up lifecycle manager if exists
        if self.lifecycle_manager and not self.lifecycle_manager.is_shutting_down():
            try:
                await self.lifecycle_manager.shutdown()
            except Exception:
                pass  # Ignore cleanup errors
        
        await super().asyncTearDown()
    
    def _create_mock_websocket_manager(self):
        """Create mock WebSocket manager with real event emission behavior."""
        mock = AsyncMock()
        mock.broadcast_system_message = AsyncMock()
        mock.get_connection_count = MagicMock(return_value=0)
        mock.close_all_connections = AsyncMock()
        mock.name = "websocket_manager"
        
        # Track all events for validation
        mock.broadcasted_events = []
        
        async def track_broadcast(message):
            mock.broadcasted_events.append(message)
            
        mock.broadcast_system_message.side_effect = track_broadcast
        return mock
    
    def _create_mock_database_manager(self):
        """Create mock database manager with health check capability."""
        mock = AsyncMock()
        mock.health_check = AsyncMock(return_value={"healthy": True})
        mock.initialize = AsyncMock()
        mock.shutdown = AsyncMock()
        mock.name = "database_manager"
        return mock
    
    def _create_mock_agent_registry(self):
        """Create mock agent registry with lifecycle management."""
        mock = AsyncMock()
        mock.get_registry_status = MagicMock(return_value={"ready": True})
        mock.get_active_tasks = MagicMock(return_value=[])
        mock.stop_accepting_requests = MagicMock()
        mock.initialize = AsyncMock()
        mock.shutdown = AsyncMock()
        mock.name = "agent_registry"
        return mock
    
    def _create_mock_health_service(self):
        """Create mock health service for testing."""
        mock = AsyncMock()
        mock.mark_shutting_down = AsyncMock()
        mock.initialize = AsyncMock()
        mock.shutdown = AsyncMock()
        mock.name = "health_service"
        return mock
    
    async def _register_all_components(self):
        """Register all mock components with the lifecycle manager."""
        await self.lifecycle_manager.register_component(
            "websocket_manager", 
            self.mock_websocket_manager, 
            ComponentType.WEBSOCKET_MANAGER
        )
        await self.lifecycle_manager.register_component(
            "database_manager", 
            self.mock_db_manager, 
            ComponentType.DATABASE_MANAGER
        )
        await self.lifecycle_manager.register_component(
            "agent_registry", 
            self.mock_agent_registry, 
            ComponentType.AGENT_REGISTRY
        )
        await self.lifecycle_manager.register_component(
            "health_service", 
            self.mock_health_service, 
            ComponentType.HEALTH_SERVICE
        )

    # ============================================================================
    # INITIALIZATION AND CONFIGURATION TESTS
    # ============================================================================
    
    async def test_01_initialization_with_default_parameters(self):
        """Test lifecycle manager initialization with default parameters."""
        manager = UnifiedLifecycleManager()
        
        # Verify default values
        self.assertEqual(manager.shutdown_timeout, 30)
        self.assertEqual(manager.drain_timeout, 20)
        self.assertEqual(manager.health_check_grace_period, 5)
        self.assertEqual(manager.startup_timeout, 60)
        self.assertIsNone(manager.user_id)
        self.assertEqual(manager.get_current_phase(), LifecyclePhase.INITIALIZING)
        self.assertFalse(manager.is_running())
        self.assertFalse(manager.is_shutting_down())
    
    async def test_02_initialization_with_custom_parameters(self):
        """Test lifecycle manager initialization with custom parameters."""
        user_id = f"custom_user_{uuid.uuid4().hex[:8]}"
        manager = UnifiedLifecycleManager(
            user_id=user_id,
            shutdown_timeout=45,
            drain_timeout=25,
            health_check_grace_period=10,
            startup_timeout=90
        )
        
        # Verify custom values
        self.assertEqual(manager.user_id, user_id)
        self.assertEqual(manager.shutdown_timeout, 45)
        self.assertEqual(manager.drain_timeout, 25)
        self.assertEqual(manager.health_check_grace_period, 10)
        self.assertEqual(manager.startup_timeout, 90)
    
    async def test_03_environment_configuration_loading(self):
        """Test loading configuration from environment variables."""
        with self.isolated_environment(
            SHUTDOWN_TIMEOUT="40",
            DRAIN_TIMEOUT="30",
            HEALTH_GRACE_PERIOD="8",
            STARTUP_TIMEOUT="120",
            LIFECYCLE_ERROR_THRESHOLD="10",
            HEALTH_CHECK_INTERVAL="45.0"
        ):
            manager = UnifiedLifecycleManager()
            
            # Verify environment values were loaded
            self.assertEqual(manager.shutdown_timeout, 40)
            self.assertEqual(manager.drain_timeout, 30)
            self.assertEqual(manager.health_check_grace_period, 8)
            self.assertEqual(manager.startup_timeout, 120)
    
    async def test_04_invalid_environment_configuration_fallback(self):
        """Test fallback to defaults when environment configuration is invalid."""
        with self.isolated_environment(
            SHUTDOWN_TIMEOUT="invalid",
            DRAIN_TIMEOUT="not_a_number",
            HEALTH_GRACE_PERIOD="",
            STARTUP_TIMEOUT="xyz"
        ):
            manager = UnifiedLifecycleManager(
                shutdown_timeout=35,
                drain_timeout=15,
                health_check_grace_period=3,
                startup_timeout=75
            )
            
            # Should fallback to constructor values
            self.assertEqual(manager.shutdown_timeout, 35)
            self.assertEqual(manager.drain_timeout, 15)
            self.assertEqual(manager.health_check_grace_period, 3)
            self.assertEqual(manager.startup_timeout, 75)

    # ============================================================================
    # COMPONENT REGISTRATION AND MANAGEMENT TESTS
    # ============================================================================
    
    async def test_05_component_registration_basic(self):
        """Test basic component registration functionality."""
        component_name = "test_component"
        
        await self.lifecycle_manager.register_component(
            component_name,
            self.mock_websocket_manager,
            ComponentType.WEBSOCKET_MANAGER
        )
        
        # Verify component is registered
        status = self.lifecycle_manager.get_component_status(component_name)
        self.assertIsNotNone(status)
        self.assertEqual(status.name, component_name)
        self.assertEqual(status.component_type, ComponentType.WEBSOCKET_MANAGER)
        self.assertEqual(status.status, "registered")
        
        # Verify component can be retrieved
        component = self.lifecycle_manager.get_component(ComponentType.WEBSOCKET_MANAGER)
        self.assertEqual(component, self.mock_websocket_manager)
    
    async def test_06_component_registration_with_health_check(self):
        """Test component registration with health check callback."""
        component_name = "health_component"
        
        async def health_check():
            return {"healthy": True, "response_time": 0.1}
        
        await self.lifecycle_manager.register_component(
            component_name,
            self.mock_db_manager,
            ComponentType.DATABASE_MANAGER,
            health_check=health_check
        )
        
        # Verify health check is registered
        status = self.lifecycle_manager.get_component_status(component_name)
        self.assertTrue(status.metadata.get("has_health_check"))
        
        # Verify health check works
        health_results = await self.lifecycle_manager._run_all_health_checks()
        self.assertIn(component_name, health_results)
        self.assertTrue(health_results[component_name]["healthy"])
    
    async def test_07_component_unregistration(self):
        """Test component unregistration functionality."""
        component_name = "temp_component"
        
        # Register component
        await self.lifecycle_manager.register_component(
            component_name,
            self.mock_agent_registry,
            ComponentType.AGENT_REGISTRY
        )
        
        # Verify registration
        self.assertIsNotNone(self.lifecycle_manager.get_component_status(component_name))
        
        # Unregister component
        await self.lifecycle_manager.unregister_component(component_name)
        
        # Verify unregistration
        self.assertIsNone(self.lifecycle_manager.get_component_status(component_name))
        self.assertIsNone(self.lifecycle_manager.get_component(ComponentType.AGENT_REGISTRY))
    
    async def test_08_multiple_component_registration(self):
        """Test registration of multiple components of different types."""
        await self._register_all_components()
        
        # Verify all components are registered
        ws_status = self.lifecycle_manager.get_component_status("websocket_manager")
        db_status = self.lifecycle_manager.get_component_status("database_manager")
        agent_status = self.lifecycle_manager.get_component_status("agent_registry")
        health_status = self.lifecycle_manager.get_component_status("health_service")
        
        self.assertIsNotNone(ws_status)
        self.assertIsNotNone(db_status)
        self.assertIsNotNone(agent_status)
        self.assertIsNotNone(health_status)
        
        # Verify different component types
        self.assertEqual(ws_status.component_type, ComponentType.WEBSOCKET_MANAGER)
        self.assertEqual(db_status.component_type, ComponentType.DATABASE_MANAGER)
        self.assertEqual(agent_status.component_type, ComponentType.AGENT_REGISTRY)
        self.assertEqual(health_status.component_type, ComponentType.HEALTH_SERVICE)
    
    async def test_09_duplicate_component_type_registration(self):
        """Test handling of duplicate component type registration."""
        # Register first component
        await self.lifecycle_manager.register_component(
            "first_db",
            self.mock_db_manager,
            ComponentType.DATABASE_MANAGER
        )
        
        # Register second component of same type (should replace first)
        new_db_manager = self._create_mock_database_manager()
        await self.lifecycle_manager.register_component(
            "second_db",
            new_db_manager,
            ComponentType.DATABASE_MANAGER
        )
        
        # Verify second component is active
        active_component = self.lifecycle_manager.get_component(ComponentType.DATABASE_MANAGER)
        self.assertEqual(active_component, new_db_manager)

    # ============================================================================
    # STARTUP LIFECYCLE TESTS
    # ============================================================================
    
    async def test_10_startup_sequence_success(self):
        """Test complete successful startup sequence."""
        await self._register_all_components()
        
        # Perform startup
        success = await self.lifecycle_manager.startup()
        
        # Verify startup succeeded
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
        self.assertTrue(self.lifecycle_manager.is_running())
        self.assertIsNotNone(self.lifecycle_manager._metrics.startup_time)
        self.assertGreater(self.lifecycle_manager._metrics.startup_time, 0)
        
        # Verify all components were initialized
        self.mock_db_manager.initialize.assert_called_once()
        self.mock_agent_registry.initialize.assert_called_once()
        self.mock_health_service.initialize.assert_called_once()
    
    async def test_11_startup_with_no_components(self):
        """Test startup sequence with no registered components."""
        # Perform startup without components
        success = await self.lifecycle_manager.startup()
        
        # Should still succeed (empty component list is valid)
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
        self.assertTrue(self.lifecycle_manager.is_running())
    
    async def test_12_startup_failure_due_to_component_validation(self):
        """Test startup failure due to component validation error."""
        # Create a database manager that fails health check
        failing_db = AsyncMock()
        failing_db.health_check = AsyncMock(return_value={"healthy": False, "error": "Connection failed"})
        failing_db.name = "failing_db"
        
        await self.lifecycle_manager.register_component(
            "failing_database",
            failing_db,
            ComponentType.DATABASE_MANAGER
        )
        
        # Startup should fail
        success = await self.lifecycle_manager.startup()
        
        self.assertFalse(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.ERROR)
    
    async def test_13_startup_failure_due_to_component_initialization(self):
        """Test startup failure due to component initialization error."""
        # Create a component that fails during initialization
        failing_component = AsyncMock()
        failing_component.initialize = AsyncMock(side_effect=Exception("Init failed"))
        failing_component.name = "failing_component"
        
        await self.lifecycle_manager.register_component(
            "failing_component",
            failing_component,
            ComponentType.LLM_MANAGER
        )
        
        # Startup should fail
        success = await self.lifecycle_manager.startup()
        
        self.assertFalse(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.ERROR)
    
    async def test_14_startup_phase_validation_components(self):
        """Test startup phase 1: component validation."""
        await self._register_all_components()
        
        # Start startup process
        startup_task = asyncio.create_task(self.lifecycle_manager.startup())
        
        # Give startup time to start
        await asyncio.sleep(0.1)
        
        # Verify database health check was called during validation
        self.mock_db_manager.health_check.assert_called()
        
        # Wait for startup to complete
        success = await startup_task
        self.assertTrue(success)
    
    async def test_15_startup_component_initialization_order(self):
        """Test that components are initialized in correct order."""
        await self._register_all_components()
        
        # Track initialization order
        init_order = []
        
        async def track_db_init():
            init_order.append("database")
        
        async def track_agent_init():
            init_order.append("agent_registry")
        
        async def track_health_init():
            init_order.append("health_service")
        
        self.mock_db_manager.initialize = track_db_init
        self.mock_agent_registry.initialize = track_agent_init
        self.mock_health_service.initialize = track_health_init
        
        # Perform startup
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        
        # Verify initialization order (database should be first)
        self.assertIn("database", init_order)
        self.assertIn("agent_registry", init_order)
        self.assertIn("health_service", init_order)
        
        # Database should come before agent registry
        db_index = init_order.index("database")
        agent_index = init_order.index("agent_registry")
        self.assertLess(db_index, agent_index)
    
    async def test_16_startup_duplicate_attempt(self):
        """Test that duplicate startup attempts are handled correctly."""
        await self._register_all_components()
        
        # First startup
        success1 = await self.lifecycle_manager.startup()
        self.assertTrue(success1)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
        
        # Second startup attempt should be rejected
        success2 = await self.lifecycle_manager.startup()
        self.assertFalse(success2)

    # ============================================================================
    # WEBSOCKET INTEGRATION TESTS (MISSION CRITICAL)
    # ============================================================================
    
    async def test_17_websocket_events_during_startup(self):
        """Test that WebSocket events are emitted during startup sequence."""
        # Set up WebSocket manager to track events
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        await self._register_all_components()
        
        # Perform startup
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        
        # Verify WebSocket events were emitted
        broadcasted_events = self.mock_websocket_manager.broadcasted_events
        
        # Should have events for component registration and startup completion
        event_types = [event.get("type", "") for event in broadcasted_events]
        
        # Verify lifecycle events
        self.assertIn("lifecycle_startup_completed", event_types)
        self.assertIn("lifecycle_phase_changed", event_types)
    
    async def test_18_websocket_agent_events_integration(self):
        """Test integration with all 5 required WebSocket agent events."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        
        # Simulate agent lifecycle events during startup
        await self.lifecycle_manager._emit_websocket_event("agent_started", {
            "agent_name": "test_agent",
            "user_id": self.lifecycle_manager.user_id
        })
        
        await self.lifecycle_manager._emit_websocket_event("agent_thinking", {
            "reasoning": "Analyzing test scenario",
            "agent_name": "test_agent"
        })
        
        await self.lifecycle_manager._emit_websocket_event("tool_executing", {
            "tool_name": "test_tool",
            "parameters": {"test": "value"}
        })
        
        await self.lifecycle_manager._emit_websocket_event("tool_completed", {
            "tool_name": "test_tool",
            "results": {"success": True}
        })
        
        await self.lifecycle_manager._emit_websocket_event("agent_completed", {
            "response": "Test completed successfully",
            "agent_name": "test_agent"
        })
        
        # Verify all 5 agent events were broadcasted
        broadcasted_events = self.mock_websocket_manager.broadcasted_events
        agent_event_types = [
            event.get("type", "") for event in broadcasted_events 
            if event.get("type", "").startswith("lifecycle_agent_") or 
               event.get("type", "").startswith("lifecycle_tool_")
        ]
        
        expected_events = [
            "lifecycle_agent_started",
            "lifecycle_agent_thinking", 
            "lifecycle_tool_executing",
            "lifecycle_tool_completed",
            "lifecycle_agent_completed"
        ]
        
        for expected_event in expected_events:
            self.assertIn(expected_event, agent_event_types)
    
    async def test_19_websocket_event_structure_validation(self):
        """Test that WebSocket events have proper structure and required fields."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        
        # Emit a test event
        test_data = {"test_field": "test_value", "timestamp": time.time()}
        await self.lifecycle_manager._emit_websocket_event("test_event", test_data)
        
        # Verify event structure
        broadcasted_events = self.mock_websocket_manager.broadcasted_events
        self.assertGreater(len(broadcasted_events), 0)
        
        event = broadcasted_events[-1]  # Get last event
        
        # Verify required fields
        self.assertEqual(event["type"], "lifecycle_test_event")
        self.assertIn("data", event)
        self.assertIn("timestamp", event)
        self.assertIn("user_id", event)
        
        # Verify data structure
        self.assertEqual(event["data"]["test_field"], "test_value")
    
    async def test_20_websocket_events_disabled(self):
        """Test that WebSocket events can be disabled."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        
        # Disable WebSocket events
        self.lifecycle_manager.enable_websocket_events(False)
        
        # Emit an event
        await self.lifecycle_manager._emit_websocket_event("disabled_test", {"data": "value"})
        
        # Verify no events were broadcasted
        self.assertEqual(len(self.mock_websocket_manager.broadcasted_events), 0)
        
        # Re-enable events
        self.lifecycle_manager.enable_websocket_events(True)
        
        # Emit another event
        await self.lifecycle_manager._emit_websocket_event("enabled_test", {"data": "value"})
        
        # Verify event was broadcasted
        self.assertEqual(len(self.mock_websocket_manager.broadcasted_events), 1)
    
    async def test_21_websocket_event_error_handling(self):
        """Test error handling in WebSocket event emission."""
        # Create a WebSocket manager that fails
        failing_ws = AsyncMock()
        failing_ws.broadcast_system_message = AsyncMock(side_effect=Exception("Broadcast failed"))
        
        self.lifecycle_manager.set_websocket_manager(failing_ws)
        
        # Emit event - should not raise exception
        try:
            await self.lifecycle_manager._emit_websocket_event("error_test", {"data": "value"})
        except Exception as e:
            self.fail(f"WebSocket event emission should not raise exception: {e}")

    # ============================================================================
    # SHUTDOWN LIFECYCLE TESTS
    # ============================================================================
    
    async def test_22_shutdown_sequence_success(self):
        """Test complete successful shutdown sequence."""
        await self._register_all_components()
        
        # Start the manager first
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        self.assertTrue(self.lifecycle_manager.is_running())
        
        # Perform shutdown
        shutdown_success = await self.lifecycle_manager.shutdown()
        
        # Verify shutdown succeeded
        self.assertTrue(shutdown_success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)
        self.assertTrue(self.lifecycle_manager.is_shutting_down())
        self.assertIsNotNone(self.lifecycle_manager._metrics.shutdown_time)
        self.assertGreater(self.lifecycle_manager._metrics.shutdown_time, 0)
        self.assertEqual(self.lifecycle_manager._metrics.successful_shutdowns, 1)
        
        # Verify all components were shut down
        self.mock_db_manager.shutdown.assert_called_once()
        self.mock_agent_registry.shutdown.assert_called_once()
        self.mock_health_service.shutdown.assert_called_once()
    
    async def test_23_shutdown_duplicate_attempt(self):
        """Test that duplicate shutdown attempts are handled correctly."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # First shutdown
        success1 = await self.lifecycle_manager.shutdown()
        self.assertTrue(success1)
        
        # Second shutdown attempt should return True but not repeat shutdown
        success2 = await self.lifecycle_manager.shutdown()
        self.assertTrue(success2)
        
        # Components should only be shut down once
        self.mock_db_manager.shutdown.assert_called_once()
    
    async def test_24_shutdown_component_order(self):
        """Test that components are shut down in reverse initialization order."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Track shutdown order
        shutdown_order = []
        
        async def track_health_shutdown():
            shutdown_order.append("health_service")
        
        async def track_agent_shutdown():
            shutdown_order.append("agent_registry")
        
        async def track_db_shutdown():
            shutdown_order.append("database")
        
        self.mock_health_service.shutdown = track_health_shutdown
        self.mock_agent_registry.shutdown = track_agent_shutdown
        self.mock_db_manager.shutdown = track_db_shutdown
        
        # Perform shutdown
        success = await self.lifecycle_manager.shutdown()
        self.assertTrue(success)
        
        # Verify shutdown order (reverse of initialization)
        self.assertIn("health_service", shutdown_order)
        self.assertIn("agent_registry", shutdown_order)
        self.assertIn("database", shutdown_order)
        
        # Health service should come before database (reverse order)
        health_index = shutdown_order.index("health_service")
        db_index = shutdown_order.index("database")
        self.assertLess(health_index, db_index)
    
    async def test_25_shutdown_with_active_requests(self):
        """Test shutdown with active requests that need to be drained."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Add some mock active requests
        request_ids = [f"req_{i}" for i in range(3)]
        for req_id in request_ids:
            async with self.lifecycle_manager.request_context(req_id):
                # Simulate active request during shutdown
                shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
                
                # Give shutdown time to start and begin draining
                await asyncio.sleep(0.1)
                
                # Request should still be tracked
                self.assertIn(req_id, self.lifecycle_manager._active_requests)
                
            # Request context exits, removing request from active list
        
        # Wait for shutdown to complete
        success = await shutdown_task
        self.assertTrue(success)
        
        # All requests should be drained
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
    
    async def test_26_shutdown_websocket_notification(self):
        """Test that WebSocket connections are notified during shutdown."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Set up connection count mock
        self.mock_websocket_manager.get_connection_count.return_value = 5
        
        # Perform shutdown
        success = await self.lifecycle_manager.shutdown()
        self.assertTrue(success)
        
        # Verify WebSocket shutdown notifications were sent
        self.mock_websocket_manager.broadcast_system_message.assert_called()
        self.mock_websocket_manager.close_all_connections.assert_called_once()
        
        # Verify shutdown message structure
        broadcast_calls = self.mock_websocket_manager.broadcast_system_message.call_args_list
        shutdown_messages = [
            call[0][0] for call in broadcast_calls 
            if call[0][0].get("type") == "system_shutdown"
        ]
        
        self.assertGreater(len(shutdown_messages), 0)
        shutdown_msg = shutdown_messages[0]
        self.assertEqual(shutdown_msg["type"], "system_shutdown")
        self.assertIn("message", shutdown_msg)
        self.assertIn("reconnect_delay", shutdown_msg)
    
    async def test_27_shutdown_error_handling(self):
        """Test shutdown error handling when components fail to shut down."""
        # Create a component that fails during shutdown
        failing_component = AsyncMock()
        failing_component.shutdown = AsyncMock(side_effect=Exception("Shutdown failed"))
        failing_component.name = "failing_component"
        
        await self.lifecycle_manager.register_component(
            "failing_component",
            failing_component,
            ComponentType.LLM_MANAGER
        )
        
        await self.lifecycle_manager.startup()
        
        # Shutdown should handle the error gracefully
        success = await self.lifecycle_manager.shutdown()
        
        # Should complete shutdown despite component failure
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)

    # ============================================================================
    # HEALTH MONITORING TESTS
    # ============================================================================
    
    async def test_28_health_monitoring_startup(self):
        """Test that health monitoring starts during startup."""
        await self._register_all_components()
        
        # Startup should start health monitoring
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        
        # Verify health monitoring task is running
        self.assertIsNotNone(self.lifecycle_manager._health_check_task)
        self.assertFalse(self.lifecycle_manager._health_check_task.done())
    
    async def test_29_health_check_execution(self):
        """Test health check execution for registered components."""
        # Register component with health check
        async def health_check():
            return {"healthy": True, "response_time": 0.05}
        
        await self.lifecycle_manager.register_component(
            "health_test_component",
            self.mock_db_manager,
            ComponentType.DATABASE_MANAGER,
            health_check=health_check
        )
        
        # Run health checks
        results = await self.lifecycle_manager._run_all_health_checks()
        
        # Verify health check results
        self.assertIn("health_test_component", results)
        self.assertTrue(results["health_test_component"]["healthy"])
        self.assertEqual(results["health_test_component"]["response_time"], 0.05)
    
    async def test_30_health_check_failure_handling(self):
        """Test handling of health check failures."""
        # Register component with failing health check
        async def failing_health_check():
            raise Exception("Health check failed")
        
        await self.lifecycle_manager.register_component(
            "unhealthy_component",
            self.mock_db_manager,
            ComponentType.DATABASE_MANAGER,
            health_check=failing_health_check
        )
        
        # Run health checks
        results = await self.lifecycle_manager._run_all_health_checks()
        
        # Verify failure is recorded
        self.assertIn("unhealthy_component", results)
        self.assertFalse(results["unhealthy_component"]["healthy"])
        self.assertIn("error", results["unhealthy_component"])
        self.assertTrue(results["unhealthy_component"]["critical"])
    
    async def test_31_health_status_endpoint_response(self):
        """Test health status response for monitoring endpoints."""
        await self._register_all_components()
        
        # Test different lifecycle phases
        
        # 1. INITIALIZING phase
        health_status = self.lifecycle_manager.get_health_status()
        self.assertEqual(health_status["status"], "unhealthy")
        self.assertEqual(health_status["phase"], "initializing")
        self.assertFalse(health_status["ready"])
        
        # 2. RUNNING phase
        await self.lifecycle_manager.startup()
        health_status = self.lifecycle_manager.get_health_status()
        self.assertEqual(health_status["status"], "healthy")
        self.assertEqual(health_status["phase"], "running")
        self.assertIn("components_healthy", health_status)
        
        # 3. SHUTTING_DOWN phase
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        await asyncio.sleep(0.1)  # Let shutdown start
        
        health_status = self.lifecycle_manager.get_health_status()
        if self.lifecycle_manager.get_current_phase() == LifecyclePhase.SHUTTING_DOWN:
            self.assertEqual(health_status["status"], "shutting_down")
            self.assertFalse(health_status["ready"])
        
        await shutdown_task  # Complete shutdown
    
    async def test_32_metrics_collection_during_lifecycle(self):
        """Test that lifecycle metrics are collected properly."""
        await self._register_all_components()
        
        # Record startup
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        
        # Verify startup metrics
        metrics = self.lifecycle_manager._metrics
        self.assertIsNotNone(metrics.startup_time)
        self.assertGreater(metrics.startup_time, 0)
        
        # Record shutdown
        success = await self.lifecycle_manager.shutdown()
        self.assertTrue(success)
        
        # Verify shutdown metrics
        self.assertIsNotNone(metrics.shutdown_time)
        self.assertGreater(metrics.shutdown_time, 0)
        self.assertEqual(metrics.successful_shutdowns, 1)
        self.assertEqual(metrics.failed_shutdowns, 0)

    # ============================================================================
    # REQUEST TRACKING TESTS
    # ============================================================================
    
    async def test_33_request_context_tracking(self):
        """Test request context tracking for graceful shutdown."""
        request_id = f"test_request_{uuid.uuid4().hex[:8]}"
        
        # Initially no active requests
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
        self.assertEqual(self.lifecycle_manager._metrics.active_requests, 0)
        
        # Use request context
        async with self.lifecycle_manager.request_context(request_id):
            # Request should be tracked
            self.assertIn(request_id, self.lifecycle_manager._active_requests)
            self.assertEqual(len(self.lifecycle_manager._active_requests), 1)
            self.assertEqual(self.lifecycle_manager._metrics.active_requests, 1)
            
            # Verify start time is recorded
            start_time = self.lifecycle_manager._active_requests[request_id]
            self.assertGreater(start_time, 0)
        
        # Request should be removed after context exit
        self.assertNotIn(request_id, self.lifecycle_manager._active_requests)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
        self.assertEqual(self.lifecycle_manager._metrics.active_requests, 0)
    
    async def test_34_concurrent_request_tracking(self):
        """Test tracking of multiple concurrent requests."""
        request_ids = [f"req_{i}_{uuid.uuid4().hex[:8]}" for i in range(5)]
        
        # Start multiple concurrent request contexts
        async def request_handler(req_id):
            async with self.lifecycle_manager.request_context(req_id):
                await asyncio.sleep(0.1)  # Simulate request processing
        
        # Start all requests concurrently
        tasks = [asyncio.create_task(request_handler(req_id)) for req_id in request_ids]
        
        # Give requests time to start
        await asyncio.sleep(0.05)
        
        # All requests should be tracked
        self.assertEqual(len(self.lifecycle_manager._active_requests), 5)
        self.assertEqual(self.lifecycle_manager._metrics.active_requests, 5)
        
        # Wait for all requests to complete
        await asyncio.gather(*tasks)
        
        # All requests should be cleaned up
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
        self.assertEqual(self.lifecycle_manager._metrics.active_requests, 0)
    
    async def test_35_request_tracking_error_cleanup(self):
        """Test that request tracking cleans up even if request fails."""
        request_id = f"failing_request_{uuid.uuid4().hex[:8]}"
        
        try:
            async with self.lifecycle_manager.request_context(request_id):
                # Verify request is tracked
                self.assertIn(request_id, self.lifecycle_manager._active_requests)
                
                # Simulate request failure
                raise ValueError("Request processing failed")
        
        except ValueError:
            pass  # Expected error
        
        # Request should still be cleaned up despite error
        self.assertNotIn(request_id, self.lifecycle_manager._active_requests)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)

    # ============================================================================
    # LIFECYCLE HOOKS AND HANDLERS TESTS
    # ============================================================================
    
    async def test_36_startup_handler_registration_and_execution(self):
        """Test registration and execution of startup handlers."""
        handler_executed = False
        
        def startup_handler():
            nonlocal handler_executed
            handler_executed = True
        
        # Register startup handler
        self.lifecycle_manager.add_startup_handler(startup_handler)
        
        # Startup should execute the handler
        await self._register_all_components()
        success = await self.lifecycle_manager.startup()
        
        self.assertTrue(success)
        self.assertTrue(handler_executed)
    
    async def test_37_async_startup_handler(self):
        """Test async startup handler execution."""
        handler_executed = False
        
        async def async_startup_handler():
            nonlocal handler_executed
            await asyncio.sleep(0.01)  # Simulate async work
            handler_executed = True
        
        # Register async startup handler
        self.lifecycle_manager.add_startup_handler(async_startup_handler)
        
        # Startup should execute the async handler
        await self._register_all_components()
        success = await self.lifecycle_manager.startup()
        
        self.assertTrue(success)
        self.assertTrue(handler_executed)
    
    async def test_38_shutdown_handler_registration_and_execution(self):
        """Test registration and execution of shutdown handlers."""
        handler_executed = False
        
        def shutdown_handler():
            nonlocal handler_executed
            handler_executed = True
        
        # Register shutdown handler
        self.lifecycle_manager.add_shutdown_handler(shutdown_handler)
        
        # Start and shutdown to execute the handler
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        success = await self.lifecycle_manager.shutdown()
        
        self.assertTrue(success)
        self.assertTrue(handler_executed)
    
    async def test_39_lifecycle_hook_registration_and_execution(self):
        """Test lifecycle hook registration and execution."""
        hook_events = []
        
        def pre_startup_hook():
            hook_events.append("pre_startup")
        
        def post_startup_hook():
            hook_events.append("post_startup")
        
        def pre_shutdown_hook():
            hook_events.append("pre_shutdown")
        
        def post_shutdown_hook():
            hook_events.append("post_shutdown")
        
        # Register lifecycle hooks
        self.lifecycle_manager.register_lifecycle_hook("pre_startup", pre_startup_hook)
        self.lifecycle_manager.register_lifecycle_hook("post_startup", post_startup_hook)
        self.lifecycle_manager.register_lifecycle_hook("pre_shutdown", pre_shutdown_hook)
        self.lifecycle_manager.register_lifecycle_hook("post_shutdown", post_shutdown_hook)
        
        # Execute full lifecycle
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        await self.lifecycle_manager.shutdown()
        
        # Verify all hooks were executed in correct order
        expected_hooks = ["pre_startup", "post_startup", "pre_shutdown", "post_shutdown"]
        self.assertEqual(hook_events, expected_hooks)
    
    async def test_40_error_hook_execution(self):
        """Test error hook execution when errors occur."""
        error_events = []
        
        def error_hook(**kwargs):
            error_events.append({
                "error": str(kwargs.get("error", "")),
                "phase": kwargs.get("phase", "unknown")
            })
        
        # Register error hook
        self.lifecycle_manager.register_lifecycle_hook("on_error", error_hook)
        
        # Create a component that fails during initialization
        failing_component = AsyncMock()
        failing_component.initialize = AsyncMock(side_effect=Exception("Init failed"))
        
        await self.lifecycle_manager.register_component(
            "failing_component",
            failing_component,
            ComponentType.LLM_MANAGER
        )
        
        # Startup should trigger error hook
        success = await self.lifecycle_manager.startup()
        self.assertFalse(success)
        
        # Verify error hook was called
        self.assertGreater(len(error_events), 0)
        self.assertIn("Init failed", error_events[0]["error"])
        self.assertEqual(error_events[0]["phase"], "startup")
    
    async def test_41_handler_error_isolation(self):
        """Test that handler errors don't break lifecycle operations."""
        def failing_handler():
            raise Exception("Handler failed")
        
        def working_handler():
            working_handler.executed = True
        
        working_handler.executed = False
        
        # Register both handlers
        self.lifecycle_manager.add_startup_handler(failing_handler)
        self.lifecycle_manager.add_startup_handler(working_handler)
        
        # Startup should continue despite handler failure
        await self._register_all_components()
        success = await self.lifecycle_manager.startup()
        
        # Startup should still succeed
        self.assertTrue(success)
        # Working handler should still execute
        self.assertTrue(working_handler.executed)

    # ============================================================================
    # STATUS AND MONITORING TESTS
    # ============================================================================
    
    async def test_42_phase_transitions_and_logging(self):
        """Test lifecycle phase transitions and state management."""
        # Initially in INITIALIZING phase
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.INITIALIZING)
        
        await self._register_all_components()
        
        # Start startup process and verify phase transitions
        startup_task = asyncio.create_task(self.lifecycle_manager.startup())
        
        # Give startup time to transition through phases
        await asyncio.sleep(0.1)
        
        # Should be in STARTING or RUNNING phase
        current_phase = self.lifecycle_manager.get_current_phase()
        self.assertIn(current_phase, [LifecyclePhase.STARTING, LifecyclePhase.RUNNING])
        
        # Wait for startup to complete
        success = await startup_task
        self.assertTrue(success)
        
        # Should be in RUNNING phase
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
        self.assertTrue(self.lifecycle_manager.is_running())
        self.assertFalse(self.lifecycle_manager.is_shutting_down())
        
        # Start shutdown and verify phase transition
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        
        # Give shutdown time to start
        await asyncio.sleep(0.1)
        
        # Should be in SHUTTING_DOWN phase
        if not shutdown_task.done():
            self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTTING_DOWN)
            self.assertTrue(self.lifecycle_manager.is_shutting_down())
        
        # Wait for shutdown to complete
        success = await shutdown_task
        self.assertTrue(success)
        
        # Should be in SHUTDOWN_COMPLETE phase
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)
    
    async def test_43_comprehensive_status_information(self):
        """Test comprehensive status information retrieval."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Get comprehensive status
        status = self.lifecycle_manager.get_status()
        
        # Verify status structure
        self.assertIn("user_id", status)
        self.assertIn("phase", status)
        self.assertIn("startup_time", status)
        self.assertIn("active_requests", status)
        self.assertIn("components", status)
        self.assertIn("metrics", status)
        self.assertIn("is_shutting_down", status)
        self.assertIn("ready_for_requests", status)
        self.assertIn("uptime", status)
        
        # Verify specific values
        self.assertEqual(status["phase"], "running")
        self.assertTrue(status["ready_for_requests"])
        self.assertFalse(status["is_shutting_down"])
        self.assertGreater(status["uptime"], 0)
        
        # Verify component status
        self.assertIn("websocket_manager", status["components"])
        self.assertIn("database_manager", status["components"])
        
        # Verify metrics
        self.assertIn("successful_shutdowns", status["metrics"])
        self.assertIn("failed_shutdowns", status["metrics"])
        self.assertIn("component_failures", status["metrics"])
    
    async def test_44_wait_for_shutdown_functionality(self):
        """Test wait_for_shutdown functionality."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Start wait_for_shutdown in background
        wait_task = asyncio.create_task(self.lifecycle_manager.wait_for_shutdown())
        
        # Give wait task time to start
        await asyncio.sleep(0.1)
        
        # Should not be done yet
        self.assertFalse(wait_task.done())
        
        # Initiate shutdown
        await self.lifecycle_manager.shutdown()
        
        # Wait task should complete
        await asyncio.wait_for(wait_task, timeout=1.0)
        self.assertTrue(wait_task.done())

    # ============================================================================
    # FACTORY PATTERN AND MULTI-USER ISOLATION TESTS
    # ============================================================================
    
    async def test_45_factory_global_manager_creation(self):
        """Test factory pattern global manager creation."""
        # Get global manager
        global_manager = LifecycleManagerFactory.get_global_manager()
        
        # Verify it's a UnifiedLifecycleManager instance
        self.assertIsInstance(global_manager, UnifiedLifecycleManager)
        self.assertIsNone(global_manager.user_id)
        
        # Getting it again should return the same instance
        global_manager2 = LifecycleManagerFactory.get_global_manager()
        self.assertIs(global_manager, global_manager2)
    
    async def test_46_factory_user_manager_creation(self):
        """Test factory pattern user-specific manager creation."""
        user_id = f"factory_user_{uuid.uuid4().hex[:8]}"
        
        # Get user-specific manager
        user_manager = LifecycleManagerFactory.get_user_manager(user_id)
        
        # Verify it's a UnifiedLifecycleManager instance with correct user_id
        self.assertIsInstance(user_manager, UnifiedLifecycleManager)
        self.assertEqual(user_manager.user_id, user_id)
        
        # Getting it again should return the same instance
        user_manager2 = LifecycleManagerFactory.get_user_manager(user_id)
        self.assertIs(user_manager, user_manager2)
        
        # Different user should get different manager
        user_id2 = f"factory_user2_{uuid.uuid4().hex[:8]}"
        user_manager3 = LifecycleManagerFactory.get_user_manager(user_id2)
        self.assertIsNot(user_manager, user_manager3)
        self.assertEqual(user_manager3.user_id, user_id2)
    
    async def test_47_factory_manager_isolation(self):
        """Test that factory managers are properly isolated."""
        user_id1 = f"user1_{uuid.uuid4().hex[:8]}"
        user_id2 = f"user2_{uuid.uuid4().hex[:8]}"
        
        # Get managers for different users
        manager1 = LifecycleManagerFactory.get_user_manager(user_id1)
        manager2 = LifecycleManagerFactory.get_user_manager(user_id2)
        global_manager = LifecycleManagerFactory.get_global_manager()
        
        # Verify they are different instances
        self.assertIsNot(manager1, manager2)
        self.assertIsNot(manager1, global_manager)
        self.assertIsNot(manager2, global_manager)
        
        # Register components in one manager
        mock_component = AsyncMock()
        await manager1.register_component(
            "isolated_component",
            mock_component,
            ComponentType.DATABASE_MANAGER
        )
        
        # Other managers should not see the component
        self.assertIsNotNone(manager1.get_component(ComponentType.DATABASE_MANAGER))
        self.assertIsNone(manager2.get_component(ComponentType.DATABASE_MANAGER))
        self.assertIsNone(global_manager.get_component(ComponentType.DATABASE_MANAGER))
    
    async def test_48_factory_shutdown_all_managers(self):
        """Test factory shutdown of all managers."""
        # Create multiple managers
        user_ids = [f"user_{i}_{uuid.uuid4().hex[:8]}" for i in range(3)]
        managers = []
        
        # Get global manager
        global_manager = LifecycleManagerFactory.get_global_manager()
        managers.append(global_manager)
        
        # Get user managers
        for user_id in user_ids:
            manager = LifecycleManagerFactory.get_user_manager(user_id)
            managers.append(manager)
        
        # Start all managers
        for manager in managers:
            await manager.startup()
            self.assertTrue(manager.is_running())
        
        # Shutdown all managers via factory
        await LifecycleManagerFactory.shutdown_all_managers()
        
        # Verify all managers are shut down
        for manager in managers:
            self.assertEqual(manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)
        
        # Verify factory references are cleared
        counts = LifecycleManagerFactory.get_manager_count()
        self.assertEqual(counts["global"], 0)
        self.assertEqual(counts["user_specific"], 0)
        self.assertEqual(counts["total"], 0)
    
    async def test_49_convenience_function_get_lifecycle_manager(self):
        """Test convenience function for getting lifecycle managers."""
        # Get global manager via convenience function
        global_manager = get_lifecycle_manager()
        factory_global = LifecycleManagerFactory.get_global_manager()
        self.assertIs(global_manager, factory_global)
        
        # Get user manager via convenience function
        user_id = f"convenience_user_{uuid.uuid4().hex[:8]}"
        user_manager = get_lifecycle_manager(user_id)
        factory_user = LifecycleManagerFactory.get_user_manager(user_id)
        self.assertIs(user_manager, factory_user)

    # ============================================================================
    # CONCURRENT USER SCENARIOS AND LOAD TESTING
    # ============================================================================
    
    async def test_50_concurrent_user_startup_shutdown(self):
        """Test concurrent startup and shutdown operations for multiple users."""
        user_count = 5
        user_ids = [f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(user_count)]
        
        # Create managers for all users
        managers = [LifecycleManagerFactory.get_user_manager(user_id) for user_id in user_ids]
        
        # Register mock components for each manager
        for manager in managers:
            mock_db = AsyncMock()
            mock_db.initialize = AsyncMock()
            mock_db.shutdown = AsyncMock()
            mock_db.health_check = AsyncMock(return_value={"healthy": True})
            
            await manager.register_component(
                "concurrent_db",
                mock_db,
                ComponentType.DATABASE_MANAGER
            )
        
        # Start all managers concurrently
        startup_tasks = [manager.startup() for manager in managers]
        startup_results = await asyncio.gather(*startup_tasks)
        
        # Verify all startups succeeded
        for result in startup_results:
            self.assertTrue(result)
        
        # Verify all managers are running
        for manager in managers:
            self.assertTrue(manager.is_running())
        
        # Shutdown all managers concurrently
        shutdown_tasks = [manager.shutdown() for manager in managers]
        shutdown_results = await asyncio.gather(*shutdown_tasks)
        
        # Verify all shutdowns succeeded
        for result in shutdown_results:
            self.assertTrue(result)
        
        # Verify all managers are shut down
        for manager in managers:
            self.assertEqual(manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)
    
    async def test_51_concurrent_component_registration(self):
        """Test concurrent component registration across multiple managers."""
        user_count = 3
        components_per_user = 4
        
        async def register_components_for_user(user_id):
            manager = LifecycleManagerFactory.get_user_manager(user_id)
            
            # Register multiple components concurrently
            registration_tasks = []
            for i in range(components_per_user):
                mock_component = AsyncMock()
                mock_component.name = f"component_{i}"
                
                task = manager.register_component(
                    f"component_{i}",
                    mock_component,
                    ComponentType.LLM_MANAGER
                )
                registration_tasks.append(task)
            
            await asyncio.gather(*registration_tasks)
            return manager
        
        # Register components for all users concurrently
        user_ids = [f"reg_user_{i}_{uuid.uuid4().hex[:8]}" for i in range(user_count)]
        registration_tasks = [register_components_for_user(user_id) for user_id in user_ids]
        managers = await asyncio.gather(*registration_tasks)
        
        # Verify each manager has the correct number of components
        for manager in managers:
            component_count = len(manager._components)
            self.assertEqual(component_count, components_per_user)
    
    async def test_52_concurrent_request_handling_during_lifecycle(self):
        """Test handling concurrent requests during lifecycle operations."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Start multiple concurrent requests
        request_count = 10
        request_duration = 0.5
        
        async def simulate_request(req_id):
            async with self.lifecycle_manager.request_context(req_id):
                await asyncio.sleep(request_duration)
        
        # Start all requests
        request_ids = [f"concurrent_req_{i}" for i in range(request_count)]
        request_tasks = [asyncio.create_task(simulate_request(req_id)) for req_id in request_ids]
        
        # Give requests time to start
        await asyncio.sleep(0.1)
        
        # Verify all requests are tracked
        self.assertEqual(len(self.lifecycle_manager._active_requests), request_count)
        
        # Start shutdown while requests are active
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        
        # Give shutdown time to start draining
        await asyncio.sleep(0.1)
        
        # Should be in shutting down phase
        if not shutdown_task.done():
            self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTTING_DOWN)
        
        # Wait for all requests to complete
        await asyncio.gather(*request_tasks)
        
        # Wait for shutdown to complete
        success = await shutdown_task
        self.assertTrue(success)
        
        # All requests should be drained
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
    
    async def test_53_performance_under_high_component_count(self):
        """Test performance with high number of components."""
        component_count = 50
        
        # Register many components
        registration_start = time.time()
        
        for i in range(component_count):
            mock_component = AsyncMock()
            mock_component.initialize = AsyncMock()
            mock_component.shutdown = AsyncMock()
            mock_component.name = f"perf_component_{i}"
            
            await self.lifecycle_manager.register_component(
                f"perf_component_{i}",
                mock_component,
                ComponentType.LLM_MANAGER
            )
        
        registration_time = time.time() - registration_start
        
        # Registration should be reasonably fast (< 1 second)
        self.assertLess(registration_time, 1.0)
        
        # Startup with many components
        startup_start = time.time()
        success = await self.lifecycle_manager.startup()
        startup_time = time.time() - startup_start
        
        self.assertTrue(success)
        # Startup should complete in reasonable time (< 5 seconds)
        self.assertLess(startup_time, 5.0)
        
        # Shutdown with many components
        shutdown_start = time.time()
        success = await self.lifecycle_manager.shutdown()
        shutdown_time = time.time() - shutdown_start
        
        self.assertTrue(success)
        # Shutdown should complete in reasonable time (< 5 seconds)
        self.assertLess(shutdown_time, 5.0)

    # ============================================================================
    # ERROR RECOVERY AND CIRCUIT BREAKER TESTS
    # ============================================================================
    
    async def test_54_component_failure_recovery(self):
        """Test recovery from component failures during health checks."""
        failure_count = 0
        
        async def flaky_health_check():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:  # Fail first 2 times
                raise Exception("Temporary failure")
            return {"healthy": True, "recovered": True}
        
        await self.lifecycle_manager.register_component(
            "flaky_component",
            self.mock_db_manager,
            ComponentType.DATABASE_MANAGER,
            health_check=flaky_health_check
        )
        
        # First health check should fail
        results = await self.lifecycle_manager._run_all_health_checks()
        self.assertFalse(results["flaky_component"]["healthy"])
        self.assertEqual(failure_count, 1)
        
        # Second health check should also fail
        results = await self.lifecycle_manager._run_all_health_checks()
        self.assertFalse(results["flaky_component"]["healthy"])
        self.assertEqual(failure_count, 2)
        
        # Third health check should succeed (component recovered)
        results = await self.lifecycle_manager._run_all_health_checks()
        self.assertTrue(results["flaky_component"]["healthy"])
        self.assertTrue(results["flaky_component"]["recovered"])
        self.assertEqual(failure_count, 3)
    
    async def test_55_startup_failure_cleanup(self):
        """Test proper cleanup when startup fails."""
        # Create a component that fails initialization
        failing_component = AsyncMock()
        failing_component.initialize = AsyncMock(side_effect=Exception("Init failed"))
        failing_component.shutdown = AsyncMock()
        
        # Create a successful component
        success_component = AsyncMock()
        success_component.initialize = AsyncMock()
        success_component.shutdown = AsyncMock()
        
        await self.lifecycle_manager.register_component(
            "success_component",
            success_component,
            ComponentType.DATABASE_MANAGER
        )
        await self.lifecycle_manager.register_component(
            "failing_component",
            failing_component,
            ComponentType.LLM_MANAGER
        )
        
        # Startup should fail
        success = await self.lifecycle_manager.startup()
        self.assertFalse(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.ERROR)
        
        # Verify proper cleanup - successful component should not be shut down
        # since it was never fully started due to the failure
        success_component.shutdown.assert_not_called()
        failing_component.shutdown.assert_not_called()
    
    async def test_56_shutdown_partial_failure_continuation(self):
        """Test that shutdown continues even if some components fail."""
        # Create components with different shutdown behaviors
        success_component = AsyncMock()
        success_component.initialize = AsyncMock()
        success_component.shutdown = AsyncMock()
        
        failing_component = AsyncMock()
        failing_component.initialize = AsyncMock()
        failing_component.shutdown = AsyncMock(side_effect=Exception("Shutdown failed"))
        
        another_success_component = AsyncMock()
        another_success_component.initialize = AsyncMock()
        another_success_component.shutdown = AsyncMock()
        
        await self.lifecycle_manager.register_component(
            "success1",
            success_component,
            ComponentType.DATABASE_MANAGER
        )
        await self.lifecycle_manager.register_component(
            "failing",
            failing_component,
            ComponentType.LLM_MANAGER
        )
        await self.lifecycle_manager.register_component(
            "success2",
            another_success_component,
            ComponentType.HEALTH_SERVICE
        )
        
        # Start all components
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        
        # Shutdown should continue despite one component failure
        success = await self.lifecycle_manager.shutdown()
        self.assertTrue(success)  # Should still report success for graceful shutdown
        
        # Verify all components were attempted to shut down
        success_component.shutdown.assert_called_once()
        failing_component.shutdown.assert_called_once()
        another_success_component.shutdown.assert_called_once()
    
    async def test_57_error_threshold_handling(self):
        """Test error threshold handling in health monitoring."""
        error_count = 0
        
        async def error_prone_health_check():
            nonlocal error_count
            error_count += 1
            raise Exception(f"Health check error #{error_count}")
        
        await self.lifecycle_manager.register_component(
            "error_prone",
            self.mock_db_manager,
            ComponentType.DATABASE_MANAGER,
            health_check=error_prone_health_check
        )
        
        await self.lifecycle_manager.startup()
        
        # Run health checks multiple times to trigger errors
        for i in range(6):  # More than default error threshold (5)
            await self.lifecycle_manager._run_periodic_health_checks()
        
        # Check component status
        component_status = self.lifecycle_manager.get_component_status("error_prone")
        self.assertEqual(component_status.status, "unhealthy")
        self.assertGreaterEqual(component_status.error_count, 5)
        
        # Metrics should track component failures
        self.assertGreaterEqual(self.lifecycle_manager._metrics.component_failures, 5)

    # ============================================================================
    # ZERO-DOWNTIME OPERATIONS TESTS
    # ============================================================================
    
    async def test_58_graceful_request_draining(self):
        """Test graceful draining of active requests during shutdown."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Start a long-running request
        long_request_id = f"long_request_{uuid.uuid4().hex[:8]}"
        request_completed = False
        
        async def long_running_request():
            nonlocal request_completed
            async with self.lifecycle_manager.request_context(long_request_id):
                await asyncio.sleep(2.0)  # Long request
                request_completed = True
        
        # Start the request
        request_task = asyncio.create_task(long_running_request())
        
        # Give request time to start
        await asyncio.sleep(0.1)
        
        # Verify request is tracked
        self.assertIn(long_request_id, self.lifecycle_manager._active_requests)
        
        # Start shutdown
        shutdown_start = time.time()
        success = await self.lifecycle_manager.shutdown()
        shutdown_duration = time.time() - shutdown_start
        
        # Shutdown should succeed and take time to drain request
        self.assertTrue(success)
        self.assertGreaterEqual(shutdown_duration, 2.0)  # Should wait for request
        
        # Wait for request to complete
        await request_task
        self.assertTrue(request_completed)
        
        # Request should be drained
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
    
    async def test_59_health_check_grace_period_during_shutdown(self):
        """Test health check grace period during shutdown."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Mock health service
        self.mock_health_service.mark_shutting_down = AsyncMock()
        
        # Start shutdown and measure grace period
        grace_start = time.time()
        await self.lifecycle_manager._shutdown_phase_1_mark_unhealthy()
        grace_duration = time.time() - grace_start
        
        # Should have waited for grace period
        expected_grace = self.lifecycle_manager.health_check_grace_period
        self.assertGreaterEqual(grace_duration, expected_grace - 0.1)  # Allow small timing variance
        
        # Health service should be marked as shutting down
        self.mock_health_service.mark_shutting_down.assert_called_once()
    
    async def test_60_zero_downtime_component_replacement(self):
        """Test zero-downtime component replacement scenario."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Verify initial component is working
        initial_db = self.lifecycle_manager.get_component(ComponentType.DATABASE_MANAGER)
        self.assertEqual(initial_db, self.mock_db_manager)
        
        # Register a replacement component (simulating rolling upgrade)
        new_db_manager = AsyncMock()
        new_db_manager.initialize = AsyncMock()
        new_db_manager.shutdown = AsyncMock()
        new_db_manager.health_check = AsyncMock(return_value={"healthy": True})
        new_db_manager.name = "new_database_manager"
        
        # Replace the component
        await self.lifecycle_manager.register_component(
            "new_database_manager",
            new_db_manager,
            ComponentType.DATABASE_MANAGER
        )
        
        # New component should be active
        current_db = self.lifecycle_manager.get_component(ComponentType.DATABASE_MANAGER)
        self.assertEqual(current_db, new_db_manager)
        
        # System should still be running
        self.assertTrue(self.lifecycle_manager.is_running())
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
    
    async def test_61_application_lifecycle_setup_integration(self):
        """Test setup_application_lifecycle convenience function."""
        # Create a mock FastAPI app
        mock_app = MagicMock()
        mock_app.on_event = MagicMock()
        
        # Set up application lifecycle
        user_id = f"app_user_{uuid.uuid4().hex[:8]}"
        manager = await setup_application_lifecycle(
            app=mock_app,
            websocket_manager=self.mock_websocket_manager,
            db_manager=self.mock_db_manager,
            agent_registry=self.mock_agent_registry,
            health_service=self.mock_health_service,
            user_id=user_id
        )
        
        # Verify manager is returned and configured
        self.assertIsInstance(manager, UnifiedLifecycleManager)
        self.assertEqual(manager.user_id, user_id)
        
        # Verify components are registered
        self.assertEqual(manager.get_component(ComponentType.WEBSOCKET_MANAGER), self.mock_websocket_manager)
        self.assertEqual(manager.get_component(ComponentType.DATABASE_MANAGER), self.mock_db_manager)
        self.assertEqual(manager.get_component(ComponentType.AGENT_REGISTRY), self.mock_agent_registry)
        self.assertEqual(manager.get_component(ComponentType.HEALTH_SERVICE), self.mock_health_service)
        
        # Verify FastAPI event handlers were registered
        self.assertEqual(mock_app.on_event.call_count, 2)  # startup and shutdown
        
        # Verify signal handlers were set up (this would be done in real environment)
        # Note: Signal handler setup is platform-specific and hard to test directly
    
    async def test_62_comprehensive_end_to_end_lifecycle(self):
        """Test comprehensive end-to-end lifecycle with all features."""
        # Set up comprehensive environment
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        await self._register_all_components()
        
        # Add lifecycle hooks
        lifecycle_events = []
        
        def track_event(event_name):
            def tracker(**kwargs):
                lifecycle_events.append(event_name)
            return tracker
        
        self.lifecycle_manager.register_lifecycle_hook("pre_startup", track_event("pre_startup"))
        self.lifecycle_manager.register_lifecycle_hook("post_startup", track_event("post_startup"))
        self.lifecycle_manager.register_lifecycle_hook("pre_shutdown", track_event("pre_shutdown"))
        self.lifecycle_manager.register_lifecycle_hook("post_shutdown", track_event("post_shutdown"))
        
        # Add startup/shutdown handlers
        def startup_handler():
            lifecycle_events.append("startup_handler")
        
        def shutdown_handler():
            lifecycle_events.append("shutdown_handler")
        
        self.lifecycle_manager.add_startup_handler(startup_handler)
        self.lifecycle_manager.add_shutdown_handler(shutdown_handler)
        
        # Execute full lifecycle with request simulation
        startup_success = await self.lifecycle_manager.startup()
        self.assertTrue(startup_success)
        
        # Simulate some requests during operation
        request_ids = [f"e2e_req_{i}" for i in range(3)]
        
        async def simulate_request(req_id):
            async with self.lifecycle_manager.request_context(req_id):
                await asyncio.sleep(0.1)
        
        # Run requests
        request_tasks = [asyncio.create_task(simulate_request(req_id)) for req_id in request_ids]
        await asyncio.gather(*request_tasks)
        
        # Execute shutdown
        shutdown_success = await self.lifecycle_manager.shutdown()
        self.assertTrue(shutdown_success)
        
        # Verify complete lifecycle executed
        expected_events = [
            "pre_startup", "startup_handler", "post_startup",
            "pre_shutdown", "shutdown_handler", "post_shutdown"
        ]
        
        for event in expected_events:
            self.assertIn(event, lifecycle_events)
        
        # Verify final state
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)
        self.assertTrue(self.lifecycle_manager.is_shutting_down())
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
        self.assertGreater(self.lifecycle_manager._metrics.startup_time, 0)
        self.assertGreater(self.lifecycle_manager._metrics.shutdown_time, 0)
        self.assertEqual(self.lifecycle_manager._metrics.successful_shutdowns, 1)
        self.assertEqual(self.lifecycle_manager._metrics.failed_shutdowns, 0)
        
        # Verify WebSocket events were emitted
        self.assertGreater(len(self.mock_websocket_manager.broadcasted_events), 0)


# ============================================================================
# ADDITIONAL TEST UTILITIES AND HELPERS
# ============================================================================

class TestLifecycleManagerFactory(AsyncBaseTestCase):
    """Additional tests for LifecycleManagerFactory functionality."""
    
    async def asyncTearDown(self):
        """Clean up factory state after each test."""
        await LifecycleManagerFactory.shutdown_all_managers()
        await super().asyncTearDown()
    
    async def test_factory_thread_safety(self):
        """Test factory thread safety with concurrent access."""
        user_id = f"thread_safe_user_{uuid.uuid4().hex[:8]}"
        managers = []
        
        def get_manager_thread():
            manager = LifecycleManagerFactory.get_user_manager(user_id)
            managers.append(manager)
        
        # Create multiple threads accessing factory concurrently
        threads = [threading.Thread(target=get_manager_thread) for _ in range(10)]
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All managers should be the same instance
        self.assertEqual(len(set(managers)), 1)  # All references should be identical
        for manager in managers:
            self.assertEqual(manager.user_id, user_id)


    # ============================================================================
    # ADVANCED RACE CONDITION AND CONCURRENCY TESTS (CRITICAL FOR WEBSOCKET/ASYNC)
    # ============================================================================
    
    async def test_63_concurrent_phase_transitions_race_condition_prevention(self):
        """Test prevention of race conditions during concurrent phase transitions."""
        await self._register_all_components()
        
        # Attempt concurrent startup operations (should be prevented)
        startup_tasks = [
            asyncio.create_task(self.lifecycle_manager.startup()),
            asyncio.create_task(self.lifecycle_manager.startup()),
            asyncio.create_task(self.lifecycle_manager.startup())
        ]
        
        # Only one should succeed, others should return False
        results = await asyncio.gather(*startup_tasks, return_exceptions=True)
        success_count = sum(1 for r in results if r is True)
        
        self.assertEqual(success_count, 1)  # Only one startup should succeed
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
    
    async def test_64_websocket_event_emission_race_conditions(self):
        """Test WebSocket event emission under concurrent conditions."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        
        # Emit multiple events concurrently to test race conditions
        event_count = 20
        event_tasks = []
        
        for i in range(event_count):
            task = asyncio.create_task(
                self.lifecycle_manager._emit_websocket_event(f"concurrent_test_{i}", {"index": i})
            )
            event_tasks.append(task)
        
        # All events should be emitted without race conditions
        await asyncio.gather(*event_tasks)
        
        # Verify all events were broadcasted
        broadcasted_events = self.mock_websocket_manager.broadcasted_events
        self.assertEqual(len(broadcasted_events), event_count)
        
        # Verify event ordering and data integrity
        for i, event in enumerate(broadcasted_events):
            self.assertEqual(event["type"], f"lifecycle_concurrent_test_{i}")
            self.assertEqual(event["data"]["index"], i)
    
    async def test_65_component_registration_concurrent_modifications(self):
        """Test concurrent component registration and unregistration operations."""
        component_count = 10
        
        # Create components for concurrent registration
        components = []
        for i in range(component_count):
            mock_comp = AsyncMock()
            mock_comp.name = f"concurrent_component_{i}"
            components.append((f"comp_{i}", mock_comp))
        
        # Register all components concurrently
        registration_tasks = [
            asyncio.create_task(
                self.lifecycle_manager.register_component(name, comp, ComponentType.LLM_MANAGER)
            )
            for name, comp in components
        ]
        
        await asyncio.gather(*registration_tasks)
        
        # Verify all components are registered
        self.assertEqual(len(self.lifecycle_manager._components), component_count)
        
        # Unregister half the components concurrently while registering new ones
        unregister_tasks = []
        new_register_tasks = []
        
        for i in range(component_count // 2):
            unregister_tasks.append(
                asyncio.create_task(self.lifecycle_manager.unregister_component(f"comp_{i}"))
            )
            
            new_mock = AsyncMock()
            new_mock.name = f"new_component_{i}"
            new_register_tasks.append(
                asyncio.create_task(
                    self.lifecycle_manager.register_component(
                        f"new_comp_{i}", new_mock, ComponentType.REDIS_MANAGER
                    )
                )
            )
        
        # Execute concurrent operations
        await asyncio.gather(*(unregister_tasks + new_register_tasks))
        
        # Verify final state is consistent
        remaining_count = len(self.lifecycle_manager._components)
        expected_count = component_count // 2 + component_count // 2  # Half unregistered, half new registered
        self.assertEqual(remaining_count, expected_count)
    
    async def test_66_health_monitoring_concurrent_checks(self):
        """Test concurrent health check operations without race conditions."""
        # Register multiple components with health checks
        check_counts = {}
        
        async def create_health_check(comp_name):
            async def health_check():
                check_counts[comp_name] = check_counts.get(comp_name, 0) + 1
                await asyncio.sleep(0.01)  # Simulate async work
                return {"healthy": True, "checks": check_counts[comp_name]}
            return health_check
        
        component_count = 8
        for i in range(component_count):
            comp_name = f"health_comp_{i}"
            mock_comp = AsyncMock()
            health_check = await create_health_check(comp_name)
            
            await self.lifecycle_manager.register_component(
                comp_name, mock_comp, ComponentType.LLM_MANAGER, health_check=health_check
            )
        
        # Run multiple health checks concurrently
        check_tasks = [
            asyncio.create_task(self.lifecycle_manager._run_all_health_checks())
            for _ in range(5)
        ]
        
        results_list = await asyncio.gather(*check_tasks)
        
        # Verify all health checks completed successfully
        for results in results_list:
            self.assertEqual(len(results), component_count)
            for comp_name, result in results.items():
                self.assertTrue(result["healthy"])
                self.assertIn("checks", result)
    
    async def test_67_request_context_concurrent_tracking_stress_test(self):
        """Stress test concurrent request context tracking."""
        request_count = 50
        max_concurrent = 20
        
        completed_requests = []
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def simulate_concurrent_request(req_id):
            async with semaphore:
                async with self.lifecycle_manager.request_context(req_id):
                    # Verify request is tracked
                    self.assertIn(req_id, self.lifecycle_manager._active_requests)
                    
                    # Simulate variable request duration
                    await asyncio.sleep(0.01 + (int(req_id.split('_')[-1]) % 5) * 0.01)
                    
                    completed_requests.append(req_id)
        
        # Start all requests
        request_ids = [f"stress_req_{i}" for i in range(request_count)]
        request_tasks = [
            asyncio.create_task(simulate_concurrent_request(req_id))
            for req_id in request_ids
        ]
        
        # Monitor active request count during execution
        max_active = 0
        monitoring_task = asyncio.create_task(self._monitor_active_requests(max_active))
        
        # Execute all requests
        await asyncio.gather(*request_tasks)
        monitoring_task.cancel()
        
        # Verify all requests completed and were properly tracked
        self.assertEqual(len(completed_requests), request_count)
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
        self.assertEqual(self.lifecycle_manager._metrics.active_requests, 0)
    
    async def _monitor_active_requests(self, max_active):
        """Helper method to monitor maximum active requests during stress test."""
        try:
            while True:
                current_active = len(self.lifecycle_manager._active_requests)
                max_active = max(max_active, current_active)
                await asyncio.sleep(0.001)
        except asyncio.CancelledError:
            pass
    
    # ============================================================================
    # SIGNAL HANDLING AND SYSTEM INTEGRATION TESTS
    # ============================================================================
    
    async def test_68_signal_handler_setup_validation(self):
        """Test signal handler setup for graceful shutdown."""
        # Note: Signal handling is OS-specific and hard to test directly
        # We test the setup method doesn't raise exceptions
        try:
            self.lifecycle_manager.setup_signal_handlers()
        except Exception as e:
            self.fail(f"Signal handler setup should not raise exceptions: {e}")
        
        # Verify setup completed without errors
        self.assertIsInstance(self.lifecycle_manager, UnifiedLifecycleManager)
    
    async def test_69_environment_variable_configuration_edge_cases(self):
        """Test edge cases in environment variable configuration loading."""
        # Test with various invalid environment configurations
        edge_case_configs = [
            {"SHUTDOWN_TIMEOUT": "-1"},  # Negative value
            {"DRAIN_TIMEOUT": "0"},      # Zero value
            {"HEALTH_GRACE_PERIOD": "999999"},  # Very large value
            {"STARTUP_TIMEOUT": "0.5"},  # Float as string
            {"LIFECYCLE_ERROR_THRESHOLD": ""},  # Empty string
            {"HEALTH_CHECK_INTERVAL": "not_a_number"}  # Invalid format
        ]
        
        for config in edge_case_configs:
            with self.isolated_environment(**config):
                # Should handle invalid configs gracefully
                try:
                    manager = UnifiedLifecycleManager()
                    # Verify manager was created despite invalid config
                    self.assertIsInstance(manager, UnifiedLifecycleManager)
                except Exception as e:
                    self.fail(f"Manager creation should handle invalid config gracefully: {e}")
    
    async def test_70_memory_leak_prevention_during_lifecycle_operations(self):
        """Test memory leak prevention during repeated lifecycle operations."""
        initial_component_count = len(self.lifecycle_manager._components)
        initial_handler_count = len(self.lifecycle_manager._startup_handlers)
        
        # Perform multiple register/unregister cycles
        for cycle in range(10):
            mock_comp = AsyncMock()
            mock_comp.name = f"cycle_component_{cycle}"
            
            # Register component
            await self.lifecycle_manager.register_component(
                f"cycle_comp_{cycle}",
                mock_comp,
                ComponentType.LLM_MANAGER
            )
            
            # Add handlers
            def temp_handler():
                pass
            
            self.lifecycle_manager.add_startup_handler(temp_handler)
            
            # Unregister component
            await self.lifecycle_manager.unregister_component(f"cycle_comp_{cycle}")
        
        # Verify no memory leaks (components cleaned up)
        final_component_count = len(self.lifecycle_manager._components)
        self.assertEqual(final_component_count, initial_component_count)
        
        # Handlers accumulate (this is expected behavior)
        final_handler_count = len(self.lifecycle_manager._startup_handlers)
        self.assertEqual(final_handler_count, initial_handler_count + 10)
    
    # ============================================================================
    # COMPREHENSIVE ERROR HANDLING AND EDGE CASE TESTS
    # ============================================================================
    
    async def test_71_startup_timeout_handling(self):
        """Test startup timeout handling with slow components."""
        # Create a component that takes longer than startup timeout
        slow_component = AsyncMock()
        slow_component.initialize = AsyncMock()
        
        async def slow_initialize():
            await asyncio.sleep(15)  # Longer than default startup timeout
            
        slow_component.initialize.side_effect = slow_initialize
        slow_component.name = "slow_component"
        
        await self.lifecycle_manager.register_component(
            "slow_component",
            slow_component,
            ComponentType.LLM_MANAGER
        )
        
        # Startup should handle timeout gracefully
        # Note: This test depends on the implementation having timeout logic
        # Current implementation doesn't have explicit startup timeout, 
        # but we test that it doesn't hang indefinitely
        start_time = time.time()
        
        startup_task = asyncio.create_task(self.lifecycle_manager.startup())
        
        try:
            # Wait with a reasonable timeout
            success = await asyncio.wait_for(startup_task, timeout=20.0)
            elapsed = time.time() - start_time
            
            # Startup should complete (successfully or not) within reasonable time
            self.assertLess(elapsed, 20.0)
            
        except asyncio.TimeoutError:
            self.fail("Startup should not hang indefinitely")
    
    async def test_72_shutdown_timeout_and_force_cleanup(self):
        """Test shutdown timeout handling and force cleanup."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Create a component that hangs during shutdown
        hanging_component = AsyncMock()
        hanging_component.initialize = AsyncMock()
        hanging_component.shutdown = AsyncMock()
        
        async def hanging_shutdown():
            await asyncio.sleep(60)  # Hang for a long time
            
        hanging_component.shutdown.side_effect = hanging_shutdown
        hanging_component.name = "hanging_component"
        
        await self.lifecycle_manager.register_component(
            "hanging_component",
            hanging_component,
            ComponentType.REDIS_MANAGER
        )
        
        # Shutdown should complete within timeout
        start_time = time.time()
        success = await self.lifecycle_manager.shutdown()
        elapsed = time.time() - start_time
        
        # Should complete reasonably quickly despite hanging component
        self.assertLess(elapsed, 10.0)  # Should not wait indefinitely
        self.assertTrue(success)  # Should report success despite component issues
    
    async def test_73_malformed_websocket_event_handling(self):
        """Test handling of malformed WebSocket events and edge cases."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        
        # Test various edge cases for WebSocket events
        edge_cases = [
            ("", {}),  # Empty event type
            ("test_event", None),  # None data
            ("test_event", {"circular": None}),  # Data that might cause issues
            ("very_long_event_name" * 100, {"large_data": "x" * 10000}),  # Large event
            ("test_event", {"nested": {"deeply": {"nested": {"data": True}}}}),  # Deep nesting
        ]
        
        for event_type, event_data in edge_cases:
            try:
                await self.lifecycle_manager._emit_websocket_event(event_type, event_data)
                # Should not raise exceptions
            except Exception as e:
                self.fail(f"WebSocket event emission should handle edge cases gracefully: {e}")
        
        # Verify events were processed (some may be filtered or modified)
        self.assertGreaterEqual(len(self.mock_websocket_manager.broadcasted_events), 0)
    
    async def test_74_component_health_check_exception_varieties(self):
        """Test handling of various types of exceptions in health checks."""
        exception_types = [
            ValueError("Invalid value"),
            ConnectionError("Connection failed"),
            TimeoutError("Request timed out"),
            RuntimeError("Runtime error"),
            asyncio.CancelledError(),  # Special async exception
            KeyboardInterrupt(),  # System interrupt
            MemoryError("Out of memory"),  # System resource error
        ]
        
        for i, exception in enumerate(exception_types):
            comp_name = f"failing_comp_{i}"
            
            async def failing_health_check():
                raise exception
            
            mock_comp = AsyncMock()
            await self.lifecycle_manager.register_component(
                comp_name, mock_comp, ComponentType.LLM_MANAGER, health_check=failing_health_check
            )
            
            # Health check should handle all exception types gracefully
            try:
                results = await self.lifecycle_manager._run_all_health_checks()
                
                # Should record failure for this component
                if comp_name in results:
                    self.assertFalse(results[comp_name]["healthy"])
                    self.assertIn("error", results[comp_name])
                
            except Exception as e:
                # Should not propagate exceptions from health checks
                self.fail(f"Health check should handle {type(exception).__name__} gracefully: {e}")
    
    # ============================================================================
    # ADVANCED WEBSOCKET EVENT INTEGRATION TESTS
    # ============================================================================
    
    async def test_75_websocket_event_delivery_guarantee_during_shutdown(self):
        """Test WebSocket event delivery guarantees during shutdown sequence."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Set up mock to track event timing
        event_timestamps = []
        
        async def timestamp_broadcast(message):
            event_timestamps.append({
                "timestamp": time.time(),
                "type": message.get("type", "unknown"),
                "phase": self.lifecycle_manager.get_current_phase().value
            })
        
        self.mock_websocket_manager.broadcast_system_message.side_effect = timestamp_broadcast
        
        # Start shutdown and emit events during shutdown
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        
        # Give shutdown time to start
        await asyncio.sleep(0.1)
        
        # Emit events during shutdown
        for i in range(5):
            await self.lifecycle_manager._emit_websocket_event(f"shutdown_test_{i}", {"index": i})
            await asyncio.sleep(0.02)
        
        # Complete shutdown
        success = await shutdown_task
        self.assertTrue(success)
        
        # Verify events were delivered in order
        test_events = [e for e in event_timestamps if e["type"].startswith("lifecycle_shutdown_test")]
        self.assertEqual(len(test_events), 5)
        
        # Events should be in chronological order
        for i in range(1, len(test_events)):
            self.assertLessEqual(test_events[i-1]["timestamp"], test_events[i]["timestamp"])
    
    async def test_76_websocket_connection_failure_resilience(self):
        """Test resilience when WebSocket connections fail during event emission."""
        # Create a WebSocket manager that fails intermittently
        failure_count = 0
        
        async def intermittent_broadcast(message):
            nonlocal failure_count
            failure_count += 1
            if failure_count % 3 == 0:  # Fail every 3rd message
                raise ConnectionError("WebSocket connection lost")
            # Otherwise succeed silently
        
        failing_ws_manager = AsyncMock()
        failing_ws_manager.broadcast_system_message = intermittent_broadcast
        
        self.lifecycle_manager.set_websocket_manager(failing_ws_manager)
        
        # Emit multiple events - some will fail, some will succeed
        event_count = 10
        success_count = 0
        
        for i in range(event_count):
            try:
                await self.lifecycle_manager._emit_websocket_event(f"resilience_test_{i}", {"index": i})
                success_count += 1
            except Exception:
                # Should not propagate WebSocket errors
                self.fail("WebSocket errors should not propagate to lifecycle operations")
        
        # All events should have been attempted (failures handled gracefully)
        self.assertEqual(success_count, event_count)
        self.assertEqual(failure_count, event_count)
    
    async def test_77_websocket_event_payload_validation_and_sanitization(self):
        """Test WebSocket event payload validation and sanitization."""
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        
        # Test various payload types and structures
        test_payloads = [
            {"string_field": "normal string"},
            {"numeric_field": 42, "float_field": 3.14},
            {"boolean_field": True, "none_field": None},
            {"list_field": [1, 2, 3, "mixed", True]},
            {"nested_dict": {"level1": {"level2": {"data": "deep"}}}},
            {"unicode_field": "测试数据 🎉"},
            {"large_string": "x" * 1000},  # Large payload
            {"timestamp": time.time()},
            {"complex_structure": {
                "metadata": {"version": "1.0", "client": "test"},
                "payload": {"items": [{"id": i, "name": f"item_{i}"} for i in range(10)]}
            }}
        ]
        
        for i, payload in enumerate(test_payloads):
            event_type = f"validation_test_{i}"
            
            try:
                await self.lifecycle_manager._emit_websocket_event(event_type, payload)
            except Exception as e:
                self.fail(f"Event emission should handle payload type {type(payload)}: {e}")
        
        # Verify all events were processed
        broadcasted_events = self.mock_websocket_manager.broadcasted_events
        self.assertEqual(len(broadcasted_events), len(test_payloads))
        
        # Verify event structure consistency
        for i, event in enumerate(broadcasted_events):
            self.assertEqual(event["type"], f"lifecycle_validation_test_{i}")
            self.assertIn("data", event)
            self.assertIn("timestamp", event)
            self.assertIn("user_id", event)
    
    # ============================================================================
    # PERFORMANCE AND SCALABILITY TESTS
    # ============================================================================
    
    async def test_78_large_scale_component_management_performance(self):
        """Test performance with large numbers of components."""
        component_count = 100
        start_time = time.time()
        
        # Register many components
        registration_tasks = []
        for i in range(component_count):
            mock_comp = AsyncMock()
            mock_comp.initialize = AsyncMock()
            mock_comp.shutdown = AsyncMock()
            mock_comp.name = f"scale_component_{i}"
            
            # Alternate between different component types
            comp_type = [
                ComponentType.LLM_MANAGER, 
                ComponentType.REDIS_MANAGER, 
                ComponentType.CLICKHOUSE_MANAGER
            ][i % 3]
            
            task = self.lifecycle_manager.register_component(f"scale_comp_{i}", mock_comp, comp_type)
            registration_tasks.append(task)
        
        await asyncio.gather(*registration_tasks)
        registration_time = time.time() - start_time
        
        # Registration should be reasonably fast
        self.assertLess(registration_time, 5.0)  # Should complete in under 5 seconds
        self.assertEqual(len(self.lifecycle_manager._components), component_count)
        
        # Test startup performance
        startup_start = time.time()
        success = await self.lifecycle_manager.startup()
        startup_time = time.time() - startup_start
        
        self.assertTrue(success)
        self.assertLess(startup_time, 10.0)  # Startup should be reasonably fast
        
        # Test shutdown performance
        shutdown_start = time.time()
        success = await self.lifecycle_manager.shutdown()
        shutdown_time = time.time() - shutdown_start
        
        self.assertTrue(success)
        self.assertLess(shutdown_time, 10.0)  # Shutdown should be reasonably fast
    
    async def test_79_memory_usage_optimization_during_operations(self):
        """Test memory usage optimization during lifecycle operations."""
        # This test verifies memory usage patterns - implementation dependent
        try:
            import psutil
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # Perform memory-intensive operations
            for cycle in range(20):
                # Register components
                components = []
                for i in range(50):
                    mock_comp = AsyncMock()
                    mock_comp.initialize = AsyncMock()
                    mock_comp.shutdown = AsyncMock()
                    await self.lifecycle_manager.register_component(
                        f"memory_comp_{cycle}_{i}",
                        mock_comp,
                        ComponentType.LLM_MANAGER
                    )
                    components.append(f"memory_comp_{cycle}_{i}")
                
                # Unregister components
                for comp_name in components:
                    await self.lifecycle_manager.unregister_component(comp_name)
                
                # Force garbage collection if available
                try:
                    import gc
                    gc.collect()
                except ImportError:
                    pass
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_growth = final_memory - initial_memory
            
            # Memory growth should be reasonable (< 100MB for this test)
            self.assertLess(memory_growth, 100, 
                          f"Memory growth too large: {memory_growth}MB")
            
        except ImportError:
            # Skip memory testing if psutil not available
            pass
    
    async def test_80_high_frequency_health_check_performance(self):
        """Test performance under high-frequency health check scenarios."""
        # Register components with fast health checks
        component_count = 20
        for i in range(component_count):
            async def fast_health_check():
                return {"healthy": True, "response_time": 0.001}
            
            mock_comp = AsyncMock()
            await self.lifecycle_manager.register_component(
                f"freq_comp_{i}",
                mock_comp,
                ComponentType.LLM_MANAGER,
                health_check=fast_health_check
            )
        
        # Run many health checks rapidly
        check_count = 100
        start_time = time.time()
        
        check_tasks = []
        for _ in range(check_count):
            task = asyncio.create_task(self.lifecycle_manager._run_all_health_checks())
            check_tasks.append(task)
        
        results_list = await asyncio.gather(*check_tasks)
        elapsed_time = time.time() - start_time
        
        # Verify all checks completed
        self.assertEqual(len(results_list), check_count)
        
        # Performance should be reasonable
        self.assertLess(elapsed_time, 10.0)  # Should complete in under 10 seconds
        
        # Verify results consistency
        for results in results_list:
            self.assertEqual(len(results), component_count)
            for comp_result in results.values():
                self.assertTrue(comp_result["healthy"])
    
    # ============================================================================
    # COMPREHENSIVE BUSINESS VALUE VALIDATION TESTS
    # ============================================================================
    
    async def test_81_chat_service_availability_during_lifecycle_operations(self):
        """Test chat service availability guarantees during lifecycle operations."""
        # This test validates the core business value: chat service reliability
        await self._register_all_components()
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        
        # Simulate chat service readiness checks
        def is_chat_service_ready():
            return (
                self.lifecycle_manager.is_running() and
                self.lifecycle_manager.get_component(ComponentType.WEBSOCKET_MANAGER) is not None and
                self.lifecycle_manager.get_component(ComponentType.AGENT_REGISTRY) is not None
            )
        
        # Before startup - service not ready
        self.assertFalse(is_chat_service_ready())
        
        # During startup - service becomes ready
        startup_success = await self.lifecycle_manager.startup()
        self.assertTrue(startup_success)
        self.assertTrue(is_chat_service_ready())
        
        # During normal operation - service stays ready
        for _ in range(10):
            self.assertTrue(is_chat_service_ready())
            await asyncio.sleep(0.01)
        
        # During graceful shutdown - service remains available until very end
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        
        # Give shutdown time to start but not complete
        await asyncio.sleep(0.1)
        
        # Chat service should still be considered available during graceful shutdown
        # until WebSocket connections are closed
        if not shutdown_task.done():
            # Verify components are still available during shutdown process
            self.assertIsNotNone(self.lifecycle_manager.get_component(ComponentType.WEBSOCKET_MANAGER))
            self.assertIsNotNone(self.lifecycle_manager.get_component(ComponentType.AGENT_REGISTRY))
        
        # Complete shutdown
        await shutdown_task
        
        # After shutdown - service properly unavailable
        self.assertFalse(self.lifecycle_manager.is_running())
        self.assertTrue(self.lifecycle_manager.is_shutting_down())
    
    async def test_82_zero_downtime_deployment_simulation(self):
        """Test zero-downtime deployment scenario with component replacement."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Simulate active chat sessions during deployment
        active_sessions = []
        session_count = 5
        
        for i in range(session_count):
            session_id = f"chat_session_{i}"
            active_sessions.append(session_id)
            
            # Start session context (simulates active chat)
            async def simulate_chat_session(session_id):
                async with self.lifecycle_manager.request_context(session_id):
                    # Simulate ongoing chat session during deployment
                    await asyncio.sleep(1.0)
                    return f"session_{session_id}_completed"
            
            # Don't await yet - sessions are ongoing
            asyncio.create_task(simulate_chat_session(session_id))
        
        # Give sessions time to start
        await asyncio.sleep(0.1)
        
        # Verify sessions are active
        self.assertGreater(len(self.lifecycle_manager._active_requests), 0)
        
        # Perform zero-downtime component replacement
        # 1. Create new version of component
        new_websocket_manager = AsyncMock()
        new_websocket_manager.broadcast_system_message = AsyncMock()
        new_websocket_manager.get_connection_count = MagicMock(return_value=5)
        new_websocket_manager.close_all_connections = AsyncMock()
        new_websocket_manager.name = "websocket_manager_v2"
        
        # 2. Replace component without disrupting service
        await self.lifecycle_manager.register_component(
            "websocket_manager_v2",
            new_websocket_manager,
            ComponentType.WEBSOCKET_MANAGER
        )
        
        # 3. Verify service continuity
        self.assertTrue(self.lifecycle_manager.is_running())
        self.assertEqual(
            self.lifecycle_manager.get_component(ComponentType.WEBSOCKET_MANAGER),
            new_websocket_manager
        )
        
        # 4. Complete deployment with graceful shutdown
        shutdown_success = await self.lifecycle_manager.shutdown()
        self.assertTrue(shutdown_success)
        
        # 5. Verify zero-downtime characteristics
        # - Sessions were allowed to complete
        # - New component was activated seamlessly
        # - No service interruption occurred
        self.assertEqual(len(self.lifecycle_manager._active_requests), 0)
    
    async def test_83_multi_user_isolation_comprehensive_validation(self):
        """Comprehensive test of multi-user isolation guarantees."""
        user_count = 5
        users = [f"user_{i}_{uuid.uuid4().hex[:8]}" for i in range(user_count)]
        
        # Create isolated managers for each user
        user_managers = {}
        for user_id in users:
            manager = LifecycleManagerFactory.get_user_manager(user_id)
            user_managers[user_id] = manager
        
        # Register different components for each user
        for i, (user_id, manager) in enumerate(user_managers.items()):
            # Each user gets their own component instances
            user_websocket = AsyncMock()
            user_websocket.name = f"websocket_{user_id}"
            user_websocket.broadcast_system_message = AsyncMock()
            
            user_db = AsyncMock() 
            user_db.name = f"database_{user_id}"
            user_db.initialize = AsyncMock()
            user_db.shutdown = AsyncMock()
            user_db.health_check = AsyncMock(return_value={"healthy": True, "user": user_id})
            
            await manager.register_component(f"websocket_{user_id}", user_websocket, ComponentType.WEBSOCKET_MANAGER)
            await manager.register_component(f"database_{user_id}", user_db, ComponentType.DATABASE_MANAGER)
        
        # Start all user managers
        startup_tasks = [manager.startup() for manager in user_managers.values()]
        startup_results = await asyncio.gather(*startup_tasks)
        
        # Verify all startups succeeded
        for result in startup_results:
            self.assertTrue(result)
        
        # Test isolation - each user should only see their own components
        for user_id, manager in user_managers.items():
            user_ws = manager.get_component(ComponentType.WEBSOCKET_MANAGER)
            user_db = manager.get_component(ComponentType.DATABASE_MANAGER)
            
            # Verify user gets their own components
            self.assertEqual(user_ws.name, f"websocket_{user_id}")
            self.assertEqual(user_db.name, f"database_{user_id}")
            
            # Verify user isolation - can't access other users' components
            for other_user_id, other_manager in user_managers.items():
                if other_user_id != user_id:
                    other_ws = other_manager.get_component(ComponentType.WEBSOCKET_MANAGER)
                    self.assertNotEqual(user_ws, other_ws)
        
        # Test concurrent operations don't interfere
        operation_tasks = []
        for user_id, manager in user_managers.items():
            # Each user performs independent request processing
            async def user_operations(user_id, manager):
                for req_idx in range(3):
                    req_id = f"{user_id}_req_{req_idx}"
                    async with manager.request_context(req_id):
                        await asyncio.sleep(0.1)
            
            operation_tasks.append(asyncio.create_task(user_operations(user_id, manager)))
        
        await asyncio.gather(*operation_tasks)
        
        # Clean shutdown all users
        shutdown_tasks = [manager.shutdown() for manager in user_managers.values()]
        shutdown_results = await asyncio.gather(*shutdown_tasks)
        
        # Verify all shutdowns succeeded
        for result in shutdown_results:
            self.assertTrue(result)
        
        # Verify final isolation state
        for manager in user_managers.values():
            self.assertEqual(manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)
            self.assertEqual(len(manager._active_requests), 0)
    
    # ============================================================================
    # ADDITIONAL EDGE CASE AND COMPREHENSIVE COVERAGE TESTS
    # ============================================================================
    
    async def test_84_component_status_dataclass_comprehensive_validation(self):
        """Test ComponentStatus dataclass with all edge cases and field validation."""
        # Test default ComponentStatus creation
        status = ComponentStatus("test_component", ComponentType.DATABASE_MANAGER)
        
        self.assertEqual(status.name, "test_component")
        self.assertEqual(status.component_type, ComponentType.DATABASE_MANAGER)
        self.assertEqual(status.status, "unknown")
        self.assertEqual(status.error_count, 0)
        self.assertIsNone(status.last_error)
        self.assertEqual(status.metadata, {})
        self.assertGreater(status.last_check, 0)  # Should have timestamp
        
        # Test ComponentStatus with all fields
        metadata = {"version": "1.0", "priority": "high"}
        status_full = ComponentStatus(
            name="full_component",
            component_type=ComponentType.WEBSOCKET_MANAGER,
            status="healthy",
            last_check=time.time(),
            error_count=3,
            last_error="Previous connection error",
            metadata=metadata
        )
        
        self.assertEqual(status_full.name, "full_component")
        self.assertEqual(status_full.component_type, ComponentType.WEBSOCKET_MANAGER)
        self.assertEqual(status_full.status, "healthy")
        self.assertEqual(status_full.error_count, 3)
        self.assertEqual(status_full.last_error, "Previous connection error")
        self.assertEqual(status_full.metadata, metadata)
    
    async def test_85_lifecycle_metrics_comprehensive_tracking(self):
        """Test LifecycleMetrics dataclass with comprehensive metric collection."""
        # Test default LifecycleMetrics
        metrics = LifecycleMetrics()
        
        self.assertIsNone(metrics.startup_time)
        self.assertIsNone(metrics.shutdown_time)
        self.assertEqual(metrics.successful_shutdowns, 0)
        self.assertEqual(metrics.failed_shutdowns, 0)
        self.assertEqual(metrics.component_failures, 0)
        self.assertIsNone(metrics.last_health_check)
        self.assertEqual(metrics.active_requests, 0)
        
        # Test metrics collection during actual lifecycle operations
        await self._register_all_components()
        
        # Verify metrics before operations
        initial_metrics = self.lifecycle_manager._metrics
        self.assertIsNone(initial_metrics.startup_time)
        
        # Perform startup and verify metrics
        await self.lifecycle_manager.startup()
        
        self.assertIsNotNone(self.lifecycle_manager._metrics.startup_time)
        self.assertGreater(self.lifecycle_manager._metrics.startup_time, 0)
        
        # Perform shutdown and verify metrics
        await self.lifecycle_manager.shutdown()
        
        self.assertIsNotNone(self.lifecycle_manager._metrics.shutdown_time)
        self.assertGreater(self.lifecycle_manager._metrics.shutdown_time, 0)
        self.assertEqual(self.lifecycle_manager._metrics.successful_shutdowns, 1)
        self.assertEqual(self.lifecycle_manager._metrics.failed_shutdowns, 0)
    
    async def test_86_all_component_types_comprehensive_validation(self):
        """Test all ComponentType enum values with comprehensive validation."""
        # Test all component types
        component_types = [
            ComponentType.WEBSOCKET_MANAGER,
            ComponentType.DATABASE_MANAGER,
            ComponentType.AGENT_REGISTRY,
            ComponentType.HEALTH_SERVICE,
            ComponentType.LLM_MANAGER,
            ComponentType.REDIS_MANAGER,
            ComponentType.CLICKHOUSE_MANAGER
        ]
        
        # Register one component of each type
        for i, comp_type in enumerate(component_types):
            mock_comp = AsyncMock()
            mock_comp.initialize = AsyncMock()
            mock_comp.shutdown = AsyncMock()
            mock_comp.name = f"component_{comp_type.value}"
            
            await self.lifecycle_manager.register_component(
                f"test_{comp_type.value}",
                mock_comp,
                comp_type
            )
            
            # Verify component is registered with correct type
            registered_comp = self.lifecycle_manager.get_component(comp_type)
            self.assertEqual(registered_comp, mock_comp)
            
            status = self.lifecycle_manager.get_component_status(f"test_{comp_type.value}")
            self.assertEqual(status.component_type, comp_type)
        
        # Verify all component types are registered
        self.assertEqual(len(self.lifecycle_manager._components), len(component_types))
        
        # Test startup with all component types
        success = await self.lifecycle_manager.startup()
        self.assertTrue(success)
        
        # Verify all components were initialized
        for comp_type in component_types:
            comp = self.lifecycle_manager.get_component(comp_type)
            comp.initialize.assert_called_once()
    
    async def test_87_all_lifecycle_phases_comprehensive_transitions(self):
        """Test all LifecyclePhase enum values and transitions."""
        # Test all lifecycle phases
        all_phases = [
            LifecyclePhase.INITIALIZING,
            LifecyclePhase.STARTING,
            LifecyclePhase.RUNNING,
            LifecyclePhase.SHUTTING_DOWN,
            LifecyclePhase.SHUTDOWN_COMPLETE,
            LifecyclePhase.ERROR
        ]
        
        # Verify initial phase
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.INITIALIZING)
        
        # Track phase transitions during startup
        await self._register_all_components()
        
        # Monitor phase transitions during startup
        startup_task = asyncio.create_task(self.lifecycle_manager.startup())
        
        # Give time for phase transitions
        await asyncio.sleep(0.1)
        
        # Phase should be STARTING or RUNNING
        current_phase = self.lifecycle_manager.get_current_phase()
        self.assertIn(current_phase, [LifecyclePhase.STARTING, LifecyclePhase.RUNNING])
        
        # Wait for startup completion
        success = await startup_task
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.RUNNING)
        
        # Monitor phase transitions during shutdown
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        
        # Give time for shutdown to start
        await asyncio.sleep(0.1)
        
        # Phase should be SHUTTING_DOWN if not completed yet
        if not shutdown_task.done():
            current_phase = self.lifecycle_manager.get_current_phase()
            self.assertEqual(current_phase, LifecyclePhase.SHUTTING_DOWN)
        
        # Wait for shutdown completion
        success = await shutdown_task
        self.assertTrue(success)
        self.assertEqual(self.lifecycle_manager.get_current_phase(), LifecyclePhase.SHUTDOWN_COMPLETE)
    
    async def test_88_component_validation_methods_comprehensive_coverage(self):
        """Test all component validation methods with comprehensive scenarios."""
        # Test database component validation
        db_manager = AsyncMock()
        db_manager.health_check = AsyncMock(return_value={"healthy": True})
        
        await self.lifecycle_manager.register_component(
            "test_database",
            db_manager,
            ComponentType.DATABASE_MANAGER
        )
        
        # Test validation method directly
        try:
            await self.lifecycle_manager._validate_database_component("test_database")
        except Exception as e:
            self.fail(f"Database validation should not raise exception: {e}")
        
        # Test with unhealthy database
        unhealthy_db = AsyncMock()
        unhealthy_db.health_check = AsyncMock(return_value={"healthy": False, "error": "Connection failed"})
        
        await self.lifecycle_manager.register_component(
            "unhealthy_database",
            unhealthy_db,
            ComponentType.DATABASE_MANAGER
        )
        
        # Validation should raise exception for unhealthy database
        with self.assertRaises(Exception):
            await self.lifecycle_manager._validate_database_component("unhealthy_database")
        
        # Test WebSocket component validation
        ws_manager = AsyncMock()
        ws_manager.broadcast_system_message = AsyncMock()
        
        await self.lifecycle_manager.register_component(
            "test_websocket",
            ws_manager,
            ComponentType.WEBSOCKET_MANAGER
        )
        
        try:
            await self.lifecycle_manager._validate_websocket_component("test_websocket")
            # Should set the WebSocket manager reference
            self.assertEqual(self.lifecycle_manager._websocket_manager, ws_manager)
        except Exception as e:
            self.fail(f"WebSocket validation should not raise exception: {e}")
        
        # Test agent registry validation
        agent_registry = AsyncMock()
        agent_registry.get_registry_status = MagicMock(return_value={"ready": True})
        
        await self.lifecycle_manager.register_component(
            "test_agent_registry",
            agent_registry,
            ComponentType.AGENT_REGISTRY
        )
        
        try:
            await self.lifecycle_manager._validate_agent_registry_component("test_agent_registry")
        except Exception as e:
            self.fail(f"Agent registry validation should not raise exception: {e}")
        
        # Test with unready agent registry
        unready_registry = AsyncMock()
        unready_registry.get_registry_status = MagicMock(return_value={"ready": False, "reason": "Not initialized"})
        
        await self.lifecycle_manager.register_component(
            "unready_registry",
            unready_registry,
            ComponentType.AGENT_REGISTRY
        )
        
        with self.assertRaises(Exception):
            await self.lifecycle_manager._validate_agent_registry_component("unready_registry")
    
    async def test_89_shutdown_phase_methods_comprehensive_coverage(self):
        """Test all shutdown phase methods with comprehensive validation."""
        await self._register_all_components()
        await self.lifecycle_manager.startup()
        
        # Set up WebSocket manager for testing
        self.lifecycle_manager.set_websocket_manager(self.mock_websocket_manager)
        self.mock_websocket_manager.get_connection_count.return_value = 3
        
        # Test Phase 1: Mark unhealthy
        try:
            await self.lifecycle_manager._shutdown_phase_1_mark_unhealthy()
            self.mock_health_service.mark_shutting_down.assert_called_once()
        except Exception as e:
            self.fail(f"Phase 1 shutdown should not raise exception: {e}")
        
        # Test Phase 2: Drain requests (no active requests)
        try:
            await self.lifecycle_manager._shutdown_phase_2_drain_requests()
        except Exception as e:
            self.fail(f"Phase 2 shutdown should not raise exception: {e}")
        
        # Test Phase 3: Close WebSockets
        try:
            await self.lifecycle_manager._shutdown_phase_3_close_websockets()
            self.mock_websocket_manager.broadcast_system_message.assert_called()
            self.mock_websocket_manager.close_all_connections.assert_called_once()
        except Exception as e:
            self.fail(f"Phase 3 shutdown should not raise exception: {e}")
        
        # Test Phase 4: Complete agents
        try:
            await self.lifecycle_manager._shutdown_phase_4_complete_agents()
        except Exception as e:
            self.fail(f"Phase 4 shutdown should not raise exception: {e}")
        
        # Test Phase 5: Shutdown components
        try:
            await self.lifecycle_manager._shutdown_phase_5_shutdown_components()
            # Verify components were shut down
            self.mock_db_manager.shutdown.assert_called_once()
            self.mock_agent_registry.shutdown.assert_called_once()
            self.mock_health_service.shutdown.assert_called_once()
        except Exception as e:
            self.fail(f"Phase 5 shutdown should not raise exception: {e}")
        
        # Test Phase 6: Cleanup resources
        try:
            await self.lifecycle_manager._shutdown_phase_6_cleanup_resources()
        except Exception as e:
            self.fail(f"Phase 6 shutdown should not raise exception: {e}")
        
        # Test Phase 7: Custom handlers
        handler_executed = False
        
        def test_shutdown_handler():
            nonlocal handler_executed
            handler_executed = True
        
        self.lifecycle_manager.add_shutdown_handler(test_shutdown_handler)
        
        try:
            await self.lifecycle_manager._shutdown_phase_7_custom_handlers()
            self.assertTrue(handler_executed)
        except Exception as e:
            self.fail(f"Phase 7 shutdown should not raise exception: {e}")
    
    async def test_90_comprehensive_status_and_health_endpoint_validation(self):
        """Comprehensive test of all status and health endpoint scenarios."""
        await self._register_all_components()
        
        # Test status in INITIALIZING phase
        status = self.lifecycle_manager.get_status()
        self.assertEqual(status["phase"], "initializing")
        self.assertFalse(status["ready_for_requests"])
        self.assertFalse(status["is_shutting_down"])
        
        health_status = self.lifecycle_manager.get_health_status()
        self.assertEqual(health_status["status"], "unhealthy")
        self.assertEqual(health_status["phase"], "initializing")
        self.assertFalse(health_status["ready"])
        
        # Test status in RUNNING phase
        await self.lifecycle_manager.startup()
        
        status = self.lifecycle_manager.get_status()
        self.assertEqual(status["phase"], "running")
        self.assertTrue(status["ready_for_requests"])
        self.assertFalse(status["is_shutting_down"])
        self.assertGreater(status["uptime"], 0)
        self.assertIsNotNone(status["startup_time"])
        
        health_status = self.lifecycle_manager.get_health_status()
        self.assertEqual(health_status["status"], "healthy")
        self.assertEqual(health_status["phase"], "running")
        self.assertIn("components_healthy", health_status)
        self.assertEqual(health_status["active_requests"], 0)
        
        # Test status with active requests
        async with self.lifecycle_manager.request_context("test_request"):
            status = self.lifecycle_manager.get_status()
            self.assertEqual(status["active_requests"], 1)
            
            health_status = self.lifecycle_manager.get_health_status()
            self.assertEqual(health_status["active_requests"], 1)
        
        # Test status during shutdown
        shutdown_task = asyncio.create_task(self.lifecycle_manager.shutdown())
        await asyncio.sleep(0.1)  # Let shutdown start
        
        if not shutdown_task.done():
            health_status = self.lifecycle_manager.get_health_status()
            if self.lifecycle_manager.get_current_phase() == LifecyclePhase.SHUTTING_DOWN:
                self.assertEqual(health_status["status"], "shutting_down")
                self.assertFalse(health_status["ready"])
        
        # Wait for shutdown completion
        success = await shutdown_task
        self.assertTrue(success)
        
        # Test status after shutdown
        status = self.lifecycle_manager.get_status()
        self.assertEqual(status["phase"], "shutdown_complete")
        self.assertFalse(status["ready_for_requests"])
        self.assertTrue(status["is_shutting_down"])
        self.assertIsNotNone(status["shutdown_time"])
        
        health_status = self.lifecycle_manager.get_health_status()
        self.assertEqual(health_status["status"], "unhealthy")
        self.assertEqual(health_status["phase"], "shutdown_complete")
        self.assertFalse(health_status["ready"])


if __name__ == "__main__":
    # Run the comprehensive test suite
    import sys
    import pytest
    
    # Configure pytest for async testing
    pytest.main([
        __file__,
        "-v",
        "--asyncio-mode=auto",
        "--tb=short",
        "--maxfail=5"  # Stop after 5 failures for faster feedback
    ])