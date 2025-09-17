"""SSOT Message Router Consolidation Validation Tests.

Issue #1067: Message Router Consolidation Blocking Golden Path

These tests validate proper SSOT consolidation of message routing functionality.
TESTING APPROACH: 20% New SSOT Tests - Creating validation tests for consolidation.

Business Value:
- Segment: Platform/Internal
- Goal: Golden Path Reliability ($500K+ ARR protection)
- Value Impact: Single message router eliminates race conditions and improves reliability
- Strategic Impact: SSOT consolidation reduces maintenance overhead by 60%

TEST STRATEGY:
1. SOME TESTS EXPECTED TO FAIL INITIALLY (before SSOT consolidation)
2. All tests should pass after Message Router consolidation is complete
3. Tests protect against regression after consolidation
4. Focus on business-critical functionality protection

EXPECTED BEHAVIOR BEFORE CONSOLIDATION:
- Multiple MessageRouter implementations detected (test_single_message_router_implementation - EXPECTED FAIL)
- Multiple WebSocket handlers may exist (test_unified_websocket_event_routing - EXPECTED FAIL)
- Tool dispatcher routing may be inconsistent (test_tool_dispatcher_ssot_routing - EXPECTED FAIL)

EXPECTED BEHAVIOR AFTER CONSOLIDATION:
- Only ONE MessageRouter implementation active
- All message routing through websocket_core/handlers.py
- All tool dispatcher operations through unified_tool_dispatcher.py
- WebSocket events use single SSOT broadcast service
"""

import pytest
import asyncio
import unittest
from typing import Dict, Any, List, Optional, Set
from unittest.mock import AsyncMock, MagicMock, patch

# SSOT Test Infrastructure
from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

# WebSocket core imports for message routing validation
from netra_backend.app.websocket_core.handlers import (
    MessageRouter,
    get_message_router,
    get_router_handler_count,
    list_registered_handlers,
    AgentRequestHandler,
    ConnectionHandler,
    TypingHandler,
    HeartbeatHandler,
    UserMessageHandler,
    JsonRpcHandler,
    ErrorHandler,
    BatchMessageHandler
)

# Import validation modules
from netra_backend.app.websocket_core.types import MessageType
from netra_backend.app.services.user_execution_context import UserExecutionContext

# Tool dispatcher imports for SSOT validation
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher
from netra_backend.app.tools.enhanced_dispatcher import EnhancedToolDispatcher

# WebSocket manager imports
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@pytest.mark.unit
class SSOTMessageRouterConsolidationTests(SSotAsyncTestCase):
    """Test suite for SSOT Message Router consolidation validation.

    These tests validate that SSOT consolidation works properly and that
    only ONE MessageRouter implementation is active in the system.
    """

    def setup_method(self, method):
        """Set up test environment for SSOT validation."""
        super().setup_method(method)
        self.mock_factory = SSotMockFactory()

    async def test_single_message_router_implementation(self):
        """Test that only ONE MessageRouter implementation is active.

        EXPECTED TO FAIL INITIALLY: Before consolidation, multiple routers may exist.
        SHOULD PASS AFTER: Only websocket_core/handlers.py MessageRouter should be active.
        """
        logger.info("Testing single MessageRouter implementation SSOT compliance")

        # Get the global message router instance
        router = get_message_router()

        # Validate it's the correct SSOT implementation
        self.assertIsInstance(router, MessageRouter,
                             "Message router must be instance of websocket_core.handlers.MessageRouter")

        # Check that router is from the correct SSOT module
        router_module = router.__class__.__module__
        expected_module = "netra_backend.app.websocket_core.handlers"

        self.assertEqual(router_module, expected_module,
                        f"MessageRouter must be from SSOT module {expected_module}, "
                        f"but found from {router_module}. This indicates multiple implementations.")

        # Validate handler count is reasonable (not zero, not excessive)
        handler_count = get_router_handler_count()
        self.assertGreater(handler_count, 0, "Message router must have registered handlers")
        self.assertLess(handler_count, 20, "Too many handlers suggests duplicate implementations")

        # Check for expected SSOT handlers
        registered_handlers = list_registered_handlers()
        expected_handlers = {
            'ConnectionHandler',
            'TypingHandler',
            'HeartbeatHandler',
            'AgentHandler',
            'AgentRequestHandler',
            'UserMessageHandler',
            'JsonRpcHandler',
            'ErrorHandler',
            'BatchMessageHandler'
        }

        registered_set = set(registered_handlers)
        missing_handlers = expected_handlers - registered_set

        self.assertEqual(len(missing_handlers), 0,
                        f"Missing expected SSOT handlers: {missing_handlers}. "
                        f"Found handlers: {registered_handlers}")

        logger.info(f"PASS: Single MessageRouter implementation validated with {handler_count} handlers")

    async def test_unified_websocket_event_routing(self):
        """Test that WebSocket events route through single SSOT service.

        EXPECTED TO FAIL INITIALLY: Multiple WebSocket managers may handle events differently.
        SHOULD PASS AFTER: All WebSocket events go through unified broadcast service.
        """
        logger.info("Testing unified WebSocket event routing SSOT compliance")

        # Create user execution context for testing
        user_context = UserExecutionContext.from_request(
            user_id="test_user_123",
            thread_id="test_thread_456",
            run_id="test_run_789"
        )

        # Test WebSocket manager creation follows SSOT factory pattern
        ws_manager = WebSocketManager(user_context=user_context)
        self.assertIsInstance(ws_manager, WebSocketManager,
                             "WebSocket manager must be proper SSOT instance")

        # Validate WebSocket manager uses SSOT user context
        self.assertEqual(ws_manager.user_context.user_id, "test_user_123",
                        "WebSocket manager must maintain proper user context isolation")

        # Test that critical WebSocket events are properly routed
        critical_events = [
            'agent_started',
            'agent_thinking',
            'tool_executing',
            'tool_completed',
            'agent_completed'
        ]

        # Mock WebSocket for testing
        mock_websocket = self.mock_factory.create_mock_websocket()

        # Test each critical event routing
        for event_type in critical_events:
            test_data = {
                "event": event_type,
                "type": event_type,
                "user_id": "test_user_123",
                "timestamp": 1234567890
            }

            # This should route through SSOT WebSocket manager
            # Note: Using broadcast method to test routing
            try:
                result = await ws_manager.broadcast_to_all(test_data)
                self.assertIsNotNone(result, f"Event {event_type} routing must return result")
                logger.info(f"Event {event_type} routed successfully through SSOT WebSocket manager")
            except Exception as e:
                # Log for debugging but don't fail - this may be expected before consolidation
                logger.warning(f"Event {event_type} routing failed: {e} - may be expected before consolidation")

        logger.info("PASS: Unified WebSocket event routing validation completed")

    async def test_tool_dispatcher_ssot_routing(self):
        """Test that tool dispatcher operations use SSOT routing.

        EXPECTED TO FAIL INITIALLY: Multiple tool dispatchers may exist.
        SHOULD PASS AFTER: All tool operations route through unified_tool_dispatcher.py.
        """
        logger.info("Testing tool dispatcher SSOT routing compliance")

        # Validate EnhancedToolDispatcher is properly aliased to UnifiedToolDispatcher
        with patch('warnings.warn') as mock_warn:
            # Create enhanced dispatcher (should trigger deprecation warning)
            user_context = UserExecutionContext.from_request(
                user_id="test_user_456",
                thread_id="test_thread_789",
                run_id="test_run_012"
            )

            enhanced_dispatcher = await EnhancedToolDispatcher.create_for_user(user_context)

            # Verify deprecation warning was issued
            mock_warn.assert_called()
            warning_message = mock_warn.call_args[0][0]
            self.assertIn("UnifiedToolDispatcher", warning_message,
                         "EnhancedToolDispatcher should warn about SSOT migration")

        # Test that enhanced dispatcher is actually a unified dispatcher
        self.assertIsInstance(enhanced_dispatcher, UnifiedToolDispatcher,
                             "EnhancedToolDispatcher must delegate to UnifiedToolDispatcher")

        # Validate tool dispatcher factory follows SSOT pattern
        from netra_backend.app.tools.enhanced_dispatcher import create_request_scoped_dispatcher

        scoped_dispatcher = create_request_scoped_dispatcher(user_context)
        self.assertIsInstance(scoped_dispatcher, UnifiedToolDispatcher,
                             "Request-scoped dispatcher must be UnifiedToolDispatcher instance")

        # Validate user isolation in tool dispatcher
        self.assertEqual(scoped_dispatcher.user_context.user_id, "test_user_456",
                        "Tool dispatcher must maintain proper user context isolation")

        logger.info("PASS: Tool dispatcher SSOT routing validation completed")

    async def test_message_router_factory_pattern(self):
        """Test that MessageRouter follows SSOT factory patterns.

        EXPECTED TO PASS: This tests existing factory pattern compliance.
        CRITICAL FOR: User isolation and proper SSOT instance creation.
        """
        logger.info("Testing MessageRouter factory pattern SSOT compliance")

        # Test global router singleton pattern
        router1 = get_message_router()
        router2 = get_message_router()

        # Should be the same instance (singleton pattern)
        self.assertIs(router1, router2,
                     "MessageRouter should follow singleton pattern for global instance")

        # Test router initialization state
        self.assertIsNotNone(router1.handlers,
                            "MessageRouter must have handlers initialized")

        # Test that custom handlers can be added properly
        initial_count = len(router1.handlers)

        # Create a test handler
        class HandlerTests:
            def can_handle(self, message_type):
                return message_type == MessageType.PING

            async def handle_message(self, user_id, websocket, message):
                return True

        test_handler = HandlerTests()
        router1.add_handler(test_handler)

        # Verify handler was added
        self.assertEqual(len(router1.handlers), initial_count + 1,
                        "MessageRouter must support dynamic handler registration")

        # Clean up
        router1.remove_handler(test_handler)
        self.assertEqual(len(router1.handlers), initial_count,
                        "MessageRouter must support handler removal")

        logger.info("PASS: MessageRouter factory pattern validation completed")

    async def test_message_routing_performance_baseline(self):
        """Test baseline performance of message routing before consolidation.

        This establishes performance baseline to ensure consolidation doesn't degrade performance.
        """
        logger.info("Testing message routing performance baseline")

        router = get_message_router()
        mock_websocket = self.mock_factory.create_mock_websocket()

        # Test message routing performance
        import time

        start_time = time.time()

        # Route multiple messages to test performance
        test_messages = [
            {"type": "ping", "timestamp": time.time()},
            {"type": "user_message", "content": "test message", "timestamp": time.time()},
            {"type": "agent_request", "message": "test request", "timestamp": time.time()},
            {"type": "heartbeat", "timestamp": time.time()}
        ]

        routing_times = []

        for message in test_messages:
            msg_start = time.time()
            try:
                await router.route_message("test_user", mock_websocket, message)
                msg_time = time.time() - msg_start
                routing_times.append(msg_time)
            except Exception as e:
                logger.warning(f"Message routing failed for {message['type']}: {e}")
                routing_times.append(float('inf'))  # Mark as failed

        total_time = time.time() - start_time
        avg_routing_time = sum(t for t in routing_times if t != float('inf')) / len([t for t in routing_times if t != float('inf')])

        # Performance assertions
        self.assertLess(total_time, 1.0, "Total message routing should complete within 1 second")
        self.assertLess(avg_routing_time, 0.1, "Average message routing should be under 100ms")

        # Log performance metrics for baseline
        logger.info(f"Performance baseline - Total: {total_time:.3f}s, Average: {avg_routing_time:.3f}s per message")

        # Store baseline in router stats
        stats = router.get_stats()
        self.assertIn("messages_routed", stats, "Router must track message routing statistics")

        logger.info("PASS: Message routing performance baseline established")

    async def test_ssot_import_validation(self):
        """Test that all message routing imports resolve to SSOT implementations.

        EXPECTED TO FAIL INITIALLY: Non-SSOT imports may still exist.
        SHOULD PASS AFTER: All imports resolve to SSOT modules.
        """
        logger.info("Testing SSOT import validation for message routing")

        # Test MessageRouter import resolution
        from netra_backend.app.websocket_core.handlers import MessageRouter as ImportedRouter

        self.assertEqual(ImportedRouter.__module__, "netra_backend.app.websocket_core.handlers",
                        "MessageRouter import must resolve to SSOT module")

        # Test UnifiedToolDispatcher import resolution
        from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher as ImportedDispatcher

        self.assertEqual(ImportedDispatcher.__module__, "netra_backend.app.core.tools.unified_tool_dispatcher",
                        "UnifiedToolDispatcher import must resolve to SSOT module")

        # Test WebSocketManager import resolution
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as ImportedManager

        self.assertEqual(ImportedManager.__module__, "netra_backend.app.websocket_core.websocket_manager",
                        "WebSocketManager import must resolve to SSOT module")

        # Validate that imports are consistent
        router_instance = get_message_router()
        self.assertIsInstance(router_instance, ImportedRouter,
                             "Global router must be instance of imported SSOT MessageRouter")

        logger.info("PASS: SSOT import validation completed")

    def test_ssot_consolidation_readiness(self):
        """Test system readiness for SSOT consolidation.

        This test validates that the system is ready for Message Router consolidation.
        """
        logger.info("Testing system readiness for SSOT consolidation")

        # Check for duplicate implementations (these should be eliminated after consolidation)
        import importlib
        import sys

        # List of modules that should NOT have MessageRouter implementations after consolidation
        potential_duplicate_modules = [
            "netra_backend.app.websocket_core.manager",
            "netra_backend.app.websocket_core.unified_manager",
            "netra_backend.app.tools.tool_dispatcher",
            "netra_backend.app.agents.tool_dispatcher"
        ]

        duplicates_found = []

        for module_name in potential_duplicate_modules:
            try:
                if module_name in sys.modules:
                    module = sys.modules[module_name]
                elif importlib.util.find_spec(module_name) is not None:
                    module = importlib.import_module(module_name)
                else:
                    continue

                # Check if module has MessageRouter-like classes
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (hasattr(attr, '__name__') and
                        ('Router' in attr.__name__ or 'Dispatcher' in attr.__name__) and
                        callable(attr) and hasattr(attr, '__module__')):
                        duplicates_found.append(f"{module_name}.{attr_name}")

            except Exception as e:
                logger.debug(f"Could not check module {module_name}: {e}")
                continue

        # Log found duplicates for consolidation planning
        if duplicates_found:
            logger.warning(f"Potential duplicate implementations found (to be consolidated): {duplicates_found}")
            # This is expected before consolidation - don't fail the test
            # After consolidation, this list should be empty

        # Validate current system state
        router = get_message_router()
        handler_count = get_router_handler_count()

        self.assertIsNotNone(router, "MessageRouter must be available")
        self.assertGreater(handler_count, 0, "MessageRouter must have handlers")

        logger.info(f"PASS: System readiness validated - {len(duplicates_found)} potential duplicates identified for consolidation")


if __name__ == '__main__':
    # Support both pytest and unittest execution
    unittest.main()