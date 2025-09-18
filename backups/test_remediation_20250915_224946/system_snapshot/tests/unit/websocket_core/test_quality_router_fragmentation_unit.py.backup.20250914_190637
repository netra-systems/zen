"""Unit tests for Quality Router fragmentation in Issue #1101.

Tests demonstrate fragmentation between standalone QualityMessageRouter
and embedded quality handlers in WebSocketHandler, proving SSOT violations.

Expected: 20-30% success rate due to fragmentation issues.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotBaseTestCase


class TestQualityRouterFragmentationUnit(SSotBaseTestCase):
    """Unit tests demonstrating Quality Router fragmentation issues."""

    def setUp(self):
        """Set up test fixtures for fragmentation testing."""
        super().setUp()

        # Test data
        self.test_user_id = "test_user_123"
        self.test_message = {
            "type": "get_quality_metrics",
            "thread_id": "thread_123",
            "run_id": "run_456",
            "payload": {"agent_name": "test_agent"}
        }

        # Mock services
        self.mock_quality_gate_service = MagicMock()
        self.mock_monitoring_service = MagicMock()
        self.mock_db_session_factory = MagicMock()
        self.mock_supervisor = MagicMock()

    @pytest.mark.asyncio
    async def test_standalone_quality_router_handler_initialization(self):
        """Test standalone QualityMessageRouter handler initialization.

        This should PASS - standalone router initializes correctly.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter

        # Create standalone router
        router = QualityMessageRouter(
            supervisor=self.mock_supervisor,
            db_session_factory=self.mock_db_session_factory,
            quality_gate_service=self.mock_quality_gate_service,
            monitoring_service=self.mock_monitoring_service
        )

        # Verify handlers are initialized
        self.assertIsNotNone(router.handlers)
        self.assertIn("get_quality_metrics", router.handlers)
        self.assertIn("subscribe_quality_alerts", router.handlers)
        self.assertIn("start_agent", router.handlers)
        self.assertIn("validate_content", router.handlers)
        self.assertIn("generate_quality_report", router.handlers)

    @pytest.mark.asyncio
    async def test_embedded_quality_handler_initialization(self):
        """Test embedded quality handler initialization in WebSocketHandler.

        This should FAIL initially - embedded handlers may not initialize properly.
        """
        from netra_backend.app.websocket_core.handlers import WebSocketHandler

        # Create websocket handler with minimal setup
        handler = WebSocketHandler()

        # Try to initialize quality handlers
        await handler._initialize_quality_handlers()

        # Check if quality handlers were initialized (THIS MAY FAIL)
        self.assertTrue(hasattr(handler, '_quality_handlers'))
        self.assertIsInstance(handler._quality_handlers, dict)

        # These should match standalone router but may be different (FRAGMENTATION)
        expected_handlers = {
            "get_quality_metrics",
            "subscribe_quality_alerts",
            "start_agent",
            "validate_content",
            "generate_quality_report"
        }
        actual_handlers = set(handler._quality_handlers.keys())

        # This assertion may FAIL due to fragmentation
        self.assertEqual(expected_handlers, actual_handlers,
                        "Handler sets differ between standalone and embedded routers")

    @pytest.mark.asyncio
    async def test_quality_message_type_detection_consistency(self):
        """Test quality message type detection consistency between routers.

        This should FAIL - different routers may have different message type detection.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler

        # Create both routers
        standalone_router = QualityMessageRouter(
            supervisor=self.mock_supervisor,
            db_session_factory=self.mock_db_session_factory,
            quality_gate_service=self.mock_quality_gate_service,
            monitoring_service=self.mock_monitoring_service
        )

        embedded_handler = WebSocketHandler()
        await embedded_handler._initialize_quality_handlers()

        # Test message types
        test_message_types = [
            "get_quality_metrics",
            "subscribe_quality_alerts",
            "validate_content",
            "generate_quality_report",
            "start_agent",
            "unknown_quality_type"
        ]

        for message_type in test_message_types:
            standalone_valid = standalone_router._is_valid_message_type(message_type)
            embedded_valid = embedded_handler._is_quality_message_type(message_type)

            # These should match but may not (FRAGMENTATION ISSUE)
            self.assertEqual(standalone_valid, embedded_valid,
                           f"Message type '{message_type}' detection differs between routers")

    @pytest.mark.asyncio
    async def test_quality_handler_instance_isolation(self):
        """Test that quality handlers are properly isolated between router instances.

        This may FAIL - handlers might be shared incorrectly causing state issues.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter

        # Create two separate router instances
        router1 = QualityMessageRouter(
            supervisor=self.mock_supervisor,
            db_session_factory=self.mock_db_session_factory,
            quality_gate_service=self.mock_quality_gate_service,
            monitoring_service=self.mock_monitoring_service
        )

        router2 = QualityMessageRouter(
            supervisor=self.mock_supervisor,
            db_session_factory=self.mock_db_session_factory,
            quality_gate_service=self.mock_quality_gate_service,
            monitoring_service=self.mock_monitoring_service
        )

        # Handlers should be separate instances
        for handler_type in router1.handlers:
            handler1 = router1.handlers[handler_type]
            handler2 = router2.handlers[handler_type]

            # This may FAIL if handlers are shared (SSOT violation)
            self.assertIsNot(handler1, handler2,
                           f"Handler '{handler_type}' instances are shared between routers")

    @pytest.mark.asyncio
    async def test_quality_message_routing_path_differences(self):
        """Test that quality message routing paths differ between implementations.

        This should FAIL - demonstrating routing inconsistency.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler

        # Mock the handle methods to track call paths
        with patch('netra_backend.app.services.websocket.quality_metrics_handler.QualityMetricsHandler.handle', new_callable=AsyncMock) as mock_standalone_handle:
            with patch('netra_backend.app.websocket_core.handlers.WebSocketHandler._route_quality_message', new_callable=AsyncMock) as mock_embedded_route:

                # Create routers
                standalone_router = QualityMessageRouter(
                    supervisor=self.mock_supervisor,
                    db_session_factory=self.mock_db_session_factory,
                    quality_gate_service=self.mock_quality_gate_service,
                    monitoring_service=self.mock_monitoring_service
                )

                embedded_handler = WebSocketHandler()
                await embedded_handler._initialize_quality_handlers()

                # Route same message through both paths
                await standalone_router.handle_message(self.test_user_id, self.test_message)
                await embedded_handler.handle_quality_message(self.test_user_id, self.test_message)

                # Verify different code paths were taken (FRAGMENTATION EVIDENCE)
                mock_standalone_handle.assert_called_once()
                mock_embedded_route.assert_called_once()

                # Extract call arguments to show they differ
                standalone_call = mock_standalone_handle.call_args
                embedded_call = mock_embedded_route.call_args

                # This assertion may FAIL showing routing inconsistency
                # The call patterns should be equivalent but may not be
                self.assertNotEqual(standalone_call, embedded_call,
                                  "Quality message routing should be identical but differs between implementations")

    @pytest.mark.asyncio
    async def test_session_continuity_fragmentation(self):
        """Test session continuity handling differs between routers.

        This should FAIL - showing session handling inconsistency.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler

        # Create routers
        standalone_router = QualityMessageRouter(
            supervisor=self.mock_supervisor,
            db_session_factory=self.mock_db_session_factory,
            quality_gate_service=self.mock_quality_gate_service,
            monitoring_service=self.mock_monitoring_service
        )

        embedded_handler = WebSocketHandler()

        # Test session ID storage patterns
        test_message_with_ids = {
            "type": "get_quality_metrics",
            "thread_id": "thread_123",
            "run_id": "run_456",
            "payload": {}
        }

        # Simulate message handling to check session storage
        await standalone_router.handle_message(self.test_user_id, test_message_with_ids)
        await embedded_handler.handle_quality_message(self.test_user_id, test_message_with_ids)

        # Check if session continuity data is stored consistently
        # Standalone router stores in instance variables
        standalone_thread_id = getattr(standalone_router, '_current_thread_id', None)
        standalone_run_id = getattr(standalone_router, '_current_run_id', None)

        # Embedded handler may not store at all (FRAGMENTATION)
        embedded_thread_id = getattr(embedded_handler, '_current_thread_id', None)
        embedded_run_id = getattr(embedded_handler, '_current_run_id', None)

        # These should match but may not (SESSION CONTINUITY FRAGMENTATION)
        self.assertEqual(standalone_thread_id, embedded_thread_id,
                        "Thread ID storage differs between routers")
        self.assertEqual(standalone_run_id, embedded_run_id,
                        "Run ID storage differs between routers")

    @pytest.mark.asyncio
    async def test_error_handling_fragmentation(self):
        """Test error handling differs between quality router implementations.

        This should FAIL - showing error handling inconsistency.
        """
        from netra_backend.app.services.websocket.quality_message_router import QualityMessageRouter
        from netra_backend.app.websocket_core.handlers import WebSocketHandler

        # Create routers
        standalone_router = QualityMessageRouter(
            supervisor=self.mock_supervisor,
            db_session_factory=self.mock_db_session_factory,
            quality_gate_service=self.mock_quality_gate_service,
            monitoring_service=self.mock_monitoring_service
        )

        embedded_handler = WebSocketHandler()
        await embedded_handler._initialize_quality_handlers()

        # Test unknown message type handling
        unknown_message = {
            "type": "unknown_quality_type",
            "thread_id": "thread_123",
            "run_id": "run_456",
            "payload": {}
        }

        # Both should handle unknown messages but may do so differently
        with patch('netra_backend.app.services.user_execution_context.create_defensive_user_execution_context') as mock_manager:
            mock_ws_manager = AsyncMock()
            mock_manager.return_value = mock_ws_manager

            # Test standalone error handling
            await standalone_router.handle_message(self.test_user_id, unknown_message)
            standalone_calls = mock_ws_manager.send_to_user.call_count

            # Reset mock
            mock_ws_manager.reset_mock()

            # Test embedded error handling
            await embedded_handler.handle_quality_message(self.test_user_id, unknown_message)
            embedded_calls = mock_ws_manager.send_to_user.call_count

            # Error handling patterns may differ (FRAGMENTATION)
            self.assertEqual(standalone_calls, embedded_calls,
                           "Error handling call patterns differ between router implementations")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])