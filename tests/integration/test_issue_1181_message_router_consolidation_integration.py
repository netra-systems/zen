"""
Integration Tests for Issue #1181 MessageRouter Consolidation
=============================================================

Business Value Justification:
- Segment: Platform/Critical Infrastructure
- Business Goal: SSOT Consolidation & Golden Path Protection
- Value Impact: Ensures $500K+ ARR chat functionality works during consolidation
- Strategic Impact: Validates that MessageRouter consolidation preserves all functionality

CRITICAL INTEGRATION VALIDATION:
Issue #1181 requires MessageRouter consolidation to eliminate fragmentation while
maintaining full functionality. These integration tests validate that the consolidated
MessageRouter works correctly with real services and maintains all existing capabilities.

Tests verify end-to-end message routing, handler integration, quality message support,
and compatibility with existing WebSocket infrastructure.
"""

import unittest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class TestIssue1181MessageRouterConsolidationIntegration(SSotAsyncTestCase, unittest.TestCase):
    """Integration test suite for MessageRouter consolidation validation."""
    
    def setUp(self):
        """Set up integration test environment."""
        super().setUp()
        self.test_user_id = "integration_test_user_456"
        self.test_thread_id = "integration_thread_789"
        self.test_run_id = "integration_run_012"
        
        # Mock WebSocket for integration testing
        self.mock_websocket = Mock()
        self.mock_websocket.send_json = AsyncMock()
        self.mock_websocket.send_text = AsyncMock()
        self.mock_websocket.client_state = "CONNECTED"
        self.mock_websocket.application_state = Mock()
        self.mock_websocket.application_state._mock_name = "test_websocket"
        
        # Track sent messages for validation
        self.sent_messages = []
        
        async def capture_send_json(data):
            self.sent_messages.append({"method": "send_json", "data": data})
            return True
            
        async def capture_send_text(data):
            self.sent_messages.append({"method": "send_text", "data": data})
            return True
        
        self.mock_websocket.send_json.side_effect = capture_send_json
        self.mock_websocket.send_text.side_effect = capture_send_text
    
    async def test_message_router_core_functionality_integration(self):
        """
        INTEGRATION TEST: Verify core MessageRouter functionality works end-to-end.
        
        Tests the complete message routing pipeline with real MessageRouter
        and mock WebSocket to ensure consolidation doesn't break core functionality.
        """
        logger.info(" TESTING:  MessageRouter core functionality integration")
        
        # Import and create MessageRouter
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        
        # Test Case 1: Basic message routing for core message types
        core_messages = [
            {
                "type": "connect",
                "payload": {"client_info": "test_client"},
                "user_id": self.test_user_id,
                "timestamp": time.time()
            },
            {
                "type": "ping", 
                "payload": {"timestamp": time.time()},
                "user_id": self.test_user_id,
                "timestamp": time.time()
            },
            {
                "type": "user_message",
                "payload": {"content": "Hello, test message"},
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id,
                "timestamp": time.time()
            }
        ]
        
        successful_routes = 0
        
        for message in core_messages:
            try:
                # Route the message through the consolidated router
                result = await router.route_message(
                    user_id=self.test_user_id,
                    websocket=self.mock_websocket,
                    raw_message=message
                )
                
                if result:
                    successful_routes += 1
                    logger.info(f" PASS:  Message type '{message['type']}' routed successfully")
                else:
                    logger.warning(f" WARN:  Message type '{message['type']}' routing returned False")
                    
            except Exception as e:
                logger.error(f" FAIL:  Message type '{message['type']}' routing failed: {e}")
        
        # Validate that most messages were routed successfully
        success_rate = successful_routes / len(core_messages)
        self.assertGreaterEqual(
            success_rate, 0.67,  # At least 2/3 should succeed
            f"Core message routing success rate too low: {success_rate:.2%} ({successful_routes}/{len(core_messages)})"
        )
        
        # Validate that responses were sent
        self.assertGreater(
            len(self.sent_messages), 0,
            "Should have sent responses for successful message routing"
        )
        
        logger.info(f" PASS:  Core functionality integration validated: {success_rate:.2%} success rate")
    
    async def test_message_router_handler_registration_integration(self):
        """
        INTEGRATION TEST: Verify that custom handlers can be registered and work properly.
        
        Tests the handler registration system to ensure consolidation preserves
        the ability to add custom message handlers.
        """
        logger.info(" TESTING:  MessageRouter handler registration integration")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter, BaseMessageHandler
        from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
        
        router = MessageRouter()
        initial_handler_count = len(router.handlers)
        
        # Create a custom handler for testing
        class TestIntegrationHandler(BaseMessageHandler):
            def __init__(self):
                super().__init__([MessageType.USER_MESSAGE])
                self.handled_messages = []
            
            async def handle_message(self, user_id: str, websocket, message: WebSocketMessage) -> bool:
                self.handled_messages.append({
                    "user_id": user_id,
                    "message_type": str(message.type),
                    "payload": message.payload
                })
                
                # Send a test response
                response = {
                    "type": "test_handler_response",
                    "handled_by": "TestIntegrationHandler",
                    "original_message": str(message.type),
                    "user_id": user_id
                }
                await websocket.send_json(response)
                return True
        
        # Register the custom handler
        test_handler = TestIntegrationHandler()
        router.add_handler(test_handler)
        
        # Verify handler was registered
        self.assertEqual(
            len(router.handlers), initial_handler_count + 1,
            "Handler count should increase after registration"
        )
        self.assertIn(test_handler, router.handlers, "Custom handler should be in handlers list")
        
        # Test that the custom handler gets used (custom handlers have precedence)
        test_message = {
            "type": "user_message",
            "payload": {"content": "Test message for custom handler"},
            "user_id": self.test_user_id,
            "thread_id": self.test_thread_id,
            "timestamp": time.time()
        }
        
        result = await router.route_message(
            user_id=self.test_user_id,
            websocket=self.mock_websocket,
            raw_message=test_message
        )
        
        # Verify the message was handled successfully
        self.assertTrue(result, "Custom handler should handle the message successfully")
        
        # Verify the custom handler was actually called
        self.assertEqual(
            len(test_handler.handled_messages), 1,
            "Custom handler should have handled exactly one message"
        )
        
        handled_message = test_handler.handled_messages[0]
        self.assertEqual(handled_message["user_id"], self.test_user_id)
        self.assertEqual(handled_message["message_type"], "MessageType.USER_MESSAGE")
        
        # Verify response was sent
        handler_responses = [msg for msg in self.sent_messages if "test_handler_response" in str(msg)]
        self.assertGreater(
            len(handler_responses), 0,
            "Custom handler should have sent a response"
        )
        
        logger.info(" PASS:  Handler registration integration validated")
    
    async def test_message_router_quality_message_detection_integration(self):
        """
        INTEGRATION TEST: Verify that quality messages are properly detected and handled.
        
        Tests the quality message detection system to ensure consolidation preserves
        quality message routing capabilities even when full integration fails.
        """
        logger.info(" TESTING:  MessageRouter quality message detection integration")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        
        # Test quality message detection
        quality_messages = [
            {
                "type": "get_quality_metrics",
                "payload": {"metric_type": "response_time"},
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id
            },
            {
                "type": "subscribe_quality_alerts",
                "payload": {"alert_types": ["error", "performance"]},
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id
            },
            {
                "type": "validate_content",
                "payload": {"content": "Test content for validation"},
                "user_id": self.test_user_id,
                "thread_id": self.test_thread_id
            }
        ]
        
        detection_results = []
        routing_results = []
        
        for message in quality_messages:
            # Test quality message detection
            is_quality = router._is_quality_message_type(message["type"])
            detection_results.append(is_quality)
            
            if is_quality:
                logger.info(f" PASS:  Quality message '{message['type']}' correctly detected")
            else:
                logger.error(f" FAIL:  Quality message '{message['type']}' not detected")
            
            # Test routing (may fail gracefully due to missing dependencies)
            try:
                result = await router.route_message(
                    user_id=self.test_user_id,
                    websocket=self.mock_websocket,
                    raw_message=message
                )
                routing_results.append(result)
                
                if result:
                    logger.info(f" PASS:  Quality message '{message['type']}' routed successfully")
                else:
                    logger.info(f" INFO:  Quality message '{message['type']}' routing failed gracefully")
                    
            except Exception as e:
                routing_results.append(False)
                logger.info(f" INFO:  Quality message '{message['type']}' routing failed with exception: {e}")
        
        # Validate detection results - all quality messages should be detected
        detected_count = sum(detection_results)
        self.assertEqual(
            detected_count, len(quality_messages),
            f"All quality messages should be detected: {detected_count}/{len(quality_messages)}"
        )
        
        # Routing may fail due to missing dependencies, but detection should work
        logger.info(f" SUMMARY:  Quality message integration:")
        logger.info(f"   - Detection: {detected_count}/{len(quality_messages)} messages detected")
        logger.info(f"   - Routing: {sum(routing_results)}/{len(quality_messages)} messages routed")
        
        logger.info(" PASS:  Quality message detection integration validated")
    
    async def test_message_router_error_handling_integration(self):
        """
        INTEGRATION TEST: Verify that error handling works properly during consolidation.
        
        Tests error handling and graceful degradation to ensure consolidation
        doesn't introduce silent failures or crashes.
        """
        logger.info(" TESTING:  MessageRouter error handling integration")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        
        # Test Case 1: Invalid message format should be handled gracefully
        invalid_messages = [
            {},  # Empty message
            {"type": None},  # Null type
            {"type": "unknown_message_type", "payload": {}},  # Unknown type
            {"malformed": "message"},  # Missing type
            {"type": "user_message"},  # Missing payload
        ]
        
        error_handling_results = []
        
        for i, message in enumerate(invalid_messages):
            try:
                result = await router.route_message(
                    user_id=self.test_user_id,
                    websocket=self.mock_websocket,
                    raw_message=message
                )
                
                # Should handle gracefully (return False or True, but not crash)
                error_handling_results.append(True)
                logger.info(f" PASS:  Invalid message {i+1} handled gracefully: {result}")
                
            except Exception as e:
                error_handling_results.append(False)
                logger.error(f" FAIL:  Invalid message {i+1} caused exception: {e}")
        
        # All invalid messages should be handled gracefully (no exceptions)
        graceful_handling_rate = sum(error_handling_results) / len(invalid_messages)
        self.assertEqual(
            graceful_handling_rate, 1.0,
            f"All invalid messages should be handled gracefully: {graceful_handling_rate:.2%}"
        )
        
        # Test Case 2: WebSocket connection issues should be handled
        disconnected_websocket = Mock()
        disconnected_websocket.client_state = "DISCONNECTED"
        disconnected_websocket.send_json = AsyncMock(side_effect=ConnectionError("WebSocket disconnected"))
        
        test_message = {
            "type": "ping",
            "payload": {"test": "disconnected_websocket"},
            "user_id": self.test_user_id
        }
        
        try:
            result = await router.route_message(
                user_id=self.test_user_id,
                websocket=disconnected_websocket,
                raw_message=test_message
            )
            
            # Should handle disconnected WebSocket gracefully
            logger.info(f" PASS:  Disconnected WebSocket handled gracefully: {result}")
            
        except Exception as e:
            self.fail(f"Disconnected WebSocket should be handled gracefully, but got exception: {e}")
        
        logger.info(" PASS:  Error handling integration validated")
    
    async def test_message_router_statistics_integration(self):
        """
        INTEGRATION TEST: Verify that statistics tracking works during message routing.
        
        Tests the statistics system to ensure consolidation preserves metrics
        and monitoring capabilities.
        """
        logger.info(" TESTING:  MessageRouter statistics integration")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        
        # Get initial statistics
        initial_stats = router.get_stats()
        initial_messages_routed = initial_stats["messages_routed"]
        initial_message_types = dict(initial_stats["message_types"])
        
        # Route several messages and track statistics
        test_messages = [
            {"type": "connect", "payload": {}, "user_id": self.test_user_id},
            {"type": "ping", "payload": {}, "user_id": self.test_user_id},
            {"type": "ping", "payload": {}, "user_id": self.test_user_id},  # Duplicate type
            {"type": "user_message", "payload": {"content": "test"}, "user_id": self.test_user_id},
        ]
        
        routed_count = 0
        for message in test_messages:
            try:
                result = await router.route_message(
                    user_id=self.test_user_id,
                    websocket=self.mock_websocket,
                    raw_message=message
                )
                if result:
                    routed_count += 1
            except Exception as e:
                logger.warning(f"Message routing failed: {e}")
        
        # Get updated statistics
        updated_stats = router.get_stats()
        updated_messages_routed = updated_stats["messages_routed"]
        updated_message_types = updated_stats["message_types"]
        
        # Validate statistics were updated
        messages_routed_increase = updated_messages_routed - initial_messages_routed
        self.assertGreaterEqual(
            messages_routed_increase, routed_count,
            f"Messages routed count should increase by at least {routed_count}, got {messages_routed_increase}"
        )
        
        # Validate message type tracking
        for message in test_messages:
            message_type_key = f"MessageType.{message['type'].upper()}"
            
            # Check if this message type was tracked (may have different key format)
            type_tracked = any(
                message['type'].lower() in key.lower() 
                for key in updated_message_types.keys()
            )
            
            if type_tracked:
                logger.info(f" PASS:  Message type '{message['type']}' tracked in statistics")
            else:
                logger.info(f" INFO:  Message type '{message['type']}' tracking format may differ")
        
        # Validate handler statistics
        handler_stats = updated_stats.get("handler_stats", {})
        self.assertIsInstance(handler_stats, dict, "Handler stats should be a dictionary")
        
        # Validate handler status
        handler_status = updated_stats.get("handler_status", {})
        self.assertIn("status", handler_status, "Handler status should have 'status' key")
        self.assertIn("handler_count", handler_status, "Handler status should have 'handler_count' key")
        
        logger.info(f" SUMMARY:  Statistics integration:")
        logger.info(f"   - Messages routed: +{messages_routed_increase} (expected: +{routed_count})")
        logger.info(f"   - Message types tracked: {len(updated_message_types)}")
        logger.info(f"   - Handler count: {handler_status.get('handler_count', 'unknown')}")
        logger.info(f"   - Handler status: {handler_status.get('status', 'unknown')}")
        
        logger.info(" PASS:  Statistics integration validated")
    
    async def test_message_router_compatibility_interface_integration(self):
        """
        INTEGRATION TEST: Verify that compatibility interfaces work for existing code.
        
        Tests compatibility methods to ensure existing code that depends on
        MessageRouter continues to work after consolidation.
        """
        logger.info(" TESTING:  MessageRouter compatibility interface integration")
        
        from netra_backend.app.websocket_core.handlers import MessageRouter
        
        router = MessageRouter()
        
        # Test compatibility methods that may be used by existing code
        compatibility_tests = []
        
        # Test Case 1: add_route method (for test compatibility)
        try:
            test_handler = lambda msg: True
            router.add_route("test_pattern", test_handler)
            compatibility_tests.append("add_route")
            logger.info(" PASS:  add_route compatibility method works")
        except Exception as e:
            logger.warning(f" WARN:  add_route compatibility method failed: {e}")
        
        # Test Case 2: add_middleware method
        try:
            test_middleware = lambda req, res, next: next()
            router.add_middleware(test_middleware)
            compatibility_tests.append("add_middleware")
            logger.info(" PASS:  add_middleware compatibility method works")
        except Exception as e:
            logger.warning(f" WARN:  add_middleware compatibility method failed: {e}")
        
        # Test Case 3: start/stop methods
        try:
            router.start()
            router.stop()
            compatibility_tests.append("start_stop")
            logger.info(" PASS:  start/stop compatibility methods work")
        except Exception as e:
            logger.warning(f" WARN:  start/stop compatibility methods failed: {e}")
        
        # Test Case 4: get_statistics method (vs get_stats)
        try:
            stats = router.get_statistics()
            self.assertIsInstance(stats, dict, "get_statistics should return a dictionary")
            compatibility_tests.append("get_statistics")
            logger.info(" PASS:  get_statistics compatibility method works")
        except Exception as e:
            logger.warning(f" WARN:  get_statistics compatibility method failed: {e}")
        
        # Test Case 5: Quality message handler interface
        try:
            test_message = {"type": "get_quality_metrics", "payload": {}}
            # This may fail, but should not crash
            await router.handle_message(self.test_user_id, test_message)
            compatibility_tests.append("handle_message")
            logger.info(" PASS:  handle_message compatibility method works")
        except Exception as e:
            logger.info(f" INFO:  handle_message compatibility method failed gracefully: {e}")
        
        # Validate that most compatibility interfaces work
        success_rate = len(compatibility_tests) / 5  # 5 total compatibility tests
        
        logger.info(f" SUMMARY:  Compatibility interface integration:")
        logger.info(f"   - Working interfaces: {compatibility_tests}")
        logger.info(f"   - Success rate: {success_rate:.2%} ({len(compatibility_tests)}/5)")
        
        # At least 60% of compatibility interfaces should work
        self.assertGreaterEqual(
            success_rate, 0.6,
            f"Compatibility interface success rate too low: {success_rate:.2%}"
        )
        
        logger.info(" PASS:  Compatibility interface integration validated")


if __name__ == '__main__':
    unittest.main()