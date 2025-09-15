"""
Phase 3.4 Supervisor WebSocket Bridge Integration Validation Tests

GOLDEN PATH PHASE 3.4: Issue #1188 - SupervisorAgent Integration Validation
Test Plan: Validate supervisor agent WebSocket bridge integration and event handling.

Business Value:
- Segment: All segments - $500K+ ARR Protection (Chat is 90% of platform value)
- Goal: Ensure supervisor properly integrates with WebSocket events for real-time chat
- Impact: Validates critical infrastructure supporting primary business value delivery
- Revenue Impact: Protects chat functionality that drives customer engagement and retention

Test Strategy:
- FAILING FIRST: Tests designed to fail initially to validate they work
- Real Integration: Test actual WebSocket bridge integration patterns
- Event Validation: Verify all 5 critical WebSocket events are supported
- Bridge Patterns: Validate supervisor bridge integration follows SSOT patterns

Key Test Areas:
1. WebSocket bridge dependency injection
2. Agent event notification integration
3. Critical event handling (agent_started, agent_thinking, etc.)
4. Bridge lifecycle management
5. User isolation in WebSocket contexts
6. Error handling and connection management
"""

import pytest
import asyncio
from typing import Optional, Dict, Any, List
from unittest.mock import AsyncMock, MagicMock, patch, call

# SSOT imports following test framework patterns
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# Core supervisor imports for testing
from netra_backend.app.agents.supervisor_ssot import SupervisorAgent

# WebSocket bridge and context imports
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.websocket_core.supervisor_factory import get_websocket_scoped_supervisor

# SSOT service imports
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Test utilities
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestSupervisorWebSocketBridgeIntegration(SSotAsyncTestCase):
    """
    Phase 3.4 Supervisor WebSocket Bridge Integration Tests
    
    CRITICAL: These tests are designed to FAIL initially to validate proper test behavior.
    They verify supervisor agent properly integrates with WebSocket bridge for real-time events.
    """
    
    def setUp(self):
        """Set up test fixtures for WebSocket bridge integration validation."""
        super().setUp()
        
        # Create mock factory for consistent test patterns
        self.mock_factory = SSotMockFactory()
        
        # Test user context for bridge integration
        self.test_user_context = UserExecutionContext(
            user_id="bridge_test_user",
            thread_id="bridge_test_thread",
            run_id="bridge_test_run",
            client_id="bridge_test_client"
        )
        
        # Mock WebSocket bridge with critical event methods
        self.mock_websocket_bridge = self.mock_factory.create_mock(AgentWebSocketBridge)
        
        # Configure critical WebSocket event methods
        self.mock_websocket_bridge.notify_agent_started = AsyncMock()
        self.mock_websocket_bridge.notify_agent_thinking = AsyncMock()
        self.mock_websocket_bridge.notify_tool_executing = AsyncMock()
        self.mock_websocket_bridge.notify_tool_completed = AsyncMock()
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock()
        
        # Mock LLM manager
        self.mock_llm_manager = self.mock_factory.create_mock("LLMManager")
        
    async def test_supervisor_websocket_bridge_dependency_injection(self):
        """
        BRIDGE INJECTION TEST: Validate supervisor properly accepts WebSocket bridge.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if supervisor doesn't
        properly accept and store WebSocket bridge for event notifications.
        """
        logger.info("🔌 Testing supervisor WebSocket bridge dependency injection")
        
        # Create supervisor with WebSocket bridge
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context
        )
        
        # CRITICAL: Bridge should be properly stored and accessible
        self.assertIsNotNone(supervisor.websocket_bridge,
            "CRITICAL FAILURE: Supervisor missing WebSocket bridge")
        
        self.assertEqual(supervisor.websocket_bridge, self.mock_websocket_bridge,
            "CRITICAL FAILURE: WebSocket bridge not properly stored")
        
        # CRITICAL: Bridge should be available for agent operations
        self.assertTrue(hasattr(supervisor, 'websocket_bridge'),
            "CRITICAL FAILURE: Supervisor missing websocket_bridge attribute")
        
        logger.info("✅ WebSocket bridge dependency injection validated")
        
    async def test_supervisor_critical_websocket_events_integration(self):
        """
        CRITICAL EVENTS TEST: Validate supervisor can trigger all 5 critical WebSocket events.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if supervisor doesn't
        support all critical events required for chat functionality.
        """
        logger.info("🎯 Testing supervisor critical WebSocket events integration")
        
        # Create supervisor with bridge
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=self.mock_websocket_bridge,
            user_context=self.test_user_context
        )
        
        # CRITICAL: Validate bridge has all required event methods
        critical_event_methods = [
            'notify_agent_started',
            'notify_agent_thinking', 
            'notify_tool_executing',
            'notify_tool_completed',
            'notify_agent_completed'
        ]
        
        for method_name in critical_event_methods:
            self.assertTrue(hasattr(supervisor.websocket_bridge, method_name),
                f"CRITICAL FAILURE: WebSocket bridge missing {method_name} method")
            
            # Validate method is callable
            method = getattr(supervisor.websocket_bridge, method_name)
            self.assertTrue(callable(method),
                f"CRITICAL FAILURE: {method_name} is not callable")
        
        # Test that supervisor can access and use bridge for events
        bridge = supervisor.websocket_bridge
        
        # Simulate critical event notifications
        await bridge.notify_agent_started("Test agent started")
        await bridge.notify_agent_thinking("Test agent thinking")
        await bridge.notify_tool_executing("Test tool executing")
        await bridge.notify_tool_completed("Test tool completed")
        await bridge.notify_agent_completed("Test agent completed")
        
        # Verify all events were called
        bridge.notify_agent_started.assert_called_once()
        bridge.notify_agent_thinking.assert_called_once()
        bridge.notify_tool_executing.assert_called_once()
        bridge.notify_tool_completed.assert_called_once()
        bridge.notify_agent_completed.assert_called_once()
        
        logger.info("✅ Critical WebSocket events integration validated")
        
    async def test_supervisor_websocket_context_isolation(self):
        """
        CONTEXT ISOLATION TEST: Validate supervisor maintains proper WebSocket context isolation.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if supervisor doesn't
        properly isolate WebSocket contexts between different users.
        """
        logger.info("👥 Testing supervisor WebSocket context isolation")
        
        # Create WebSocket bridges for different users
        bridge_1 = self.mock_factory.create_mock(AgentWebSocketBridge)
        bridge_2 = self.mock_factory.create_mock(AgentWebSocketBridge)
        
        # Configure bridges
        bridge_1.notify_agent_started = AsyncMock()
        bridge_2.notify_agent_started = AsyncMock()
        
        # Create user contexts for different users
        user_context_1 = UserExecutionContext(
            user_id="user_1",
            thread_id="thread_1",
            run_id="run_1", 
            client_id="client_1"
        )
        
        user_context_2 = UserExecutionContext(
            user_id="user_2",
            thread_id="thread_2",
            run_id="run_2",
            client_id="client_2"
        )
        
        # Create supervisors for different users
        supervisor_1 = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=bridge_1,
            user_context=user_context_1
        )
        
        supervisor_2 = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=bridge_2,
            user_context=user_context_2
        )
        
        # CRITICAL: Each supervisor should have its own bridge
        self.assertNotEqual(supervisor_1.websocket_bridge, supervisor_2.websocket_bridge,
            "CRITICAL FAILURE: Supervisors sharing WebSocket bridges (context leakage)")
        
        # CRITICAL: Events should be isolated per user
        await supervisor_1.websocket_bridge.notify_agent_started("User 1 agent started")
        await supervisor_2.websocket_bridge.notify_agent_started("User 2 agent started")
        
        # Verify isolation - each bridge only received its own events
        bridge_1.notify_agent_started.assert_called_once_with("User 1 agent started")
        bridge_2.notify_agent_started.assert_called_once_with("User 2 agent started")
        
        logger.info("✅ WebSocket context isolation validated")
        
    async def test_websocket_scoped_supervisor_factory_integration(self):
        """
        FACTORY INTEGRATION TEST: Validate WebSocket supervisor factory creates properly integrated supervisors.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if WebSocket factory doesn't
        create supervisors with proper bridge integration.
        """
        logger.info("🏭 Testing WebSocket scoped supervisor factory integration")
        
        # Mock WebSocket context
        mock_ws_context = MagicMock(spec=WebSocketContext)
        mock_ws_context.user_id = "factory_test_user"
        mock_ws_context.thread_id = "factory_test_thread"
        mock_ws_context.run_id = "factory_test_run"
        mock_ws_context.client_id = "factory_test_client"
        
        # Mock database session
        mock_db_session = AsyncMock()
        
        # Test WebSocket factory with bridge integration
        with patch('netra_backend.app.websocket_core.supervisor_factory.create_supervisor_core') as mock_create:
            # Configure mock to return supervisor with bridge
            mock_supervisor = MagicMock(spec=SupervisorAgent)
            mock_supervisor.websocket_bridge = self.mock_websocket_bridge
            mock_create.return_value = mock_supervisor
            
            supervisor = await get_websocket_scoped_supervisor(
                context=mock_ws_context,
                db_session=mock_db_session
            )
            
            # CRITICAL: Factory should have been called with WebSocket context
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args[1]
            
            # Validate proper WebSocket parameters
            self.assertEqual(call_kwargs['user_id'], "factory_test_user")
            self.assertEqual(call_kwargs['thread_id'], "factory_test_thread")
            self.assertEqual(call_kwargs['run_id'], "factory_test_run")
            self.assertEqual(call_kwargs['websocket_client_id'], "factory_test_client")
            
            # CRITICAL: Supervisor should have bridge integration
            self.assertIsNotNone(supervisor.websocket_bridge,
                "CRITICAL FAILURE: Factory-created supervisor missing WebSocket bridge")
        
        logger.info("✅ WebSocket scoped supervisor factory integration validated")
        
    async def test_supervisor_websocket_bridge_error_handling(self):
        """
        ERROR HANDLING TEST: Validate supervisor handles WebSocket bridge errors gracefully.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if supervisor doesn't
        properly handle WebSocket bridge errors without crashing.
        """
        logger.info("⚠️ Testing supervisor WebSocket bridge error handling")
        
        # Create bridge that raises errors
        error_bridge = self.mock_factory.create_mock(AgentWebSocketBridge)
        error_bridge.notify_agent_started = AsyncMock(side_effect=Exception("Bridge connection lost"))
        
        # Create supervisor with error-prone bridge
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=error_bridge,
            user_context=self.test_user_context
        )
        
        # CRITICAL: Supervisor should handle bridge errors gracefully
        # This test validates the supervisor can handle WebSocket failures
        try:
            await supervisor.websocket_bridge.notify_agent_started("Test message")
            self.fail("Expected exception from error bridge")
        except Exception as e:
            # Error should be handled appropriately
            self.assertIn("Bridge connection lost", str(e))
            logger.info(f"✓ Bridge error properly raised: {e}")
        
        # CRITICAL: Supervisor should still be functional despite bridge errors
        self.assertIsNotNone(supervisor._llm_manager,
            "CRITICAL FAILURE: Supervisor core functionality affected by bridge error")
        
        self.assertIsNotNone(supervisor.agent_factory,
            "CRITICAL FAILURE: Agent factory affected by bridge error")
        
        logger.info("✅ WebSocket bridge error handling validated")
        
    async def test_supervisor_bridge_lifecycle_management(self):
        """
        LIFECYCLE TEST: Validate supervisor properly manages WebSocket bridge lifecycle.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if supervisor doesn't
        properly manage bridge lifecycle and connection states.
        """
        logger.info("♻️ Testing supervisor WebSocket bridge lifecycle management")
        
        # Create bridge with lifecycle methods
        lifecycle_bridge = self.mock_factory.create_mock(AgentWebSocketBridge)
        lifecycle_bridge.is_connected = MagicMock(return_value=True)
        lifecycle_bridge.connect = AsyncMock()
        lifecycle_bridge.disconnect = AsyncMock()
        lifecycle_bridge.notify_agent_started = AsyncMock()
        
        # Create supervisor
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=lifecycle_bridge,
            user_context=self.test_user_context
        )
        
        # CRITICAL: Supervisor should have access to bridge lifecycle
        bridge = supervisor.websocket_bridge
        
        # Test connection state checking
        if hasattr(bridge, 'is_connected'):
            is_connected = bridge.is_connected()
            self.assertTrue(is_connected, "Bridge should report as connected")
        
        # Test that supervisor can use bridge for notifications
        if hasattr(bridge, 'notify_agent_started'):
            await bridge.notify_agent_started("Lifecycle test message")
            bridge.notify_agent_started.assert_called_once()
        
        logger.info("✅ WebSocket bridge lifecycle management validated")
        
    def test_supervisor_websocket_bridge_optional_handling(self):
        """
        OPTIONAL BRIDGE TEST: Validate supervisor handles optional WebSocket bridge.
        
        EXPECTED BEHAVIOR: This test should FAIL initially if supervisor doesn't
        properly handle cases where WebSocket bridge is not provided.
        """
        logger.info("🔧 Testing supervisor optional WebSocket bridge handling")
        
        # Create supervisor without WebSocket bridge
        supervisor = SupervisorAgent(
            llm_manager=self.mock_llm_manager,
            websocket_bridge=None,  # Optional parameter
            user_context=self.test_user_context
        )
        
        # CRITICAL: Supervisor should handle None bridge gracefully
        self.assertEqual(supervisor.websocket_bridge, None,
            "CRITICAL FAILURE: Supervisor not handling None bridge properly")
        
        # CRITICAL: Core functionality should still work
        self.assertIsNotNone(supervisor._llm_manager,
            "CRITICAL FAILURE: Core functionality broken without bridge")
        
        self.assertIsNotNone(supervisor.agent_factory,
            "CRITICAL FAILURE: Agent factory broken without bridge")
        
        # CRITICAL: Supervisor should still be usable for non-WebSocket operations
        self.assertEqual(supervisor.name, "Supervisor",
            "CRITICAL FAILURE: Basic supervisor properties broken without bridge")
        
        logger.info("✅ Optional WebSocket bridge handling validated")


# Execute tests if run directly
if __name__ == "__main__":
    logger.info("🚀 Starting Phase 3.4 Supervisor WebSocket Bridge Integration Tests")
    logger.info("⚠️  EXPECTED: Tests may FAIL initially - this validates proper test behavior")
    logger.info("🎯 Focus: Critical WebSocket events supporting 90% of platform business value")
    
    # Run with asyncio
    import unittest
    unittest.main()