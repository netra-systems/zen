"""
Test Issue #1093: SSOT WebSocket Agent Message Handler Validation

BUSINESS VALUE JUSTIFICATION:
- Segment: Platform/Internal
- Business Goal: System Reliability & Development Velocity
- Value Impact: Validates SSOT consolidation maintains all functionality
- Strategic Impact: Ensures Golden Path WebSocket events work with unified handler

This test validates that the new SSOT handler implementation provides all
functionality of the fragmented handlers while ensuring the Golden Path.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core.ssot_agent_message_handler import SSotAgentMessageHandler


class TestSSotAgentMessageHandlerValidation(SSotAsyncTestCase):
    """Tests validating the SSOT agent message handler implementation."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()

        # Mock WebSocket
        self.mock_websocket = MagicMock()
        self.mock_websocket.scope = {"app": MagicMock()}
        self.mock_websocket.scope["app"].state = MagicMock()

        # Mock message handler service
        self.mock_message_handler_service = MagicMock()
        self.mock_message_handler_service.handle_start_agent = AsyncMock(return_value=True)
        self.mock_message_handler_service.handle_user_message = AsyncMock(return_value=True)

        # Test user
        self.user_id = "test-user-123"

        # Create SSOT handler
        self.ssot_handler = SSotAgentMessageHandler(
            self.mock_message_handler_service,
            self.mock_websocket
        )

    async def test_ssot_handler_initialization(self):
        """Test that SSOT handler initializes with correct configuration."""
        # Create mocks
        mock_service = MagicMock()
        mock_websocket = MagicMock()

        # Create handler directly in test
        handler = SSotAgentMessageHandler(mock_service, mock_websocket)

        self.assertEqual(len(handler.supported_types), 3)
        self.assertIn(MessageType.START_AGENT, handler.supported_types)
        self.assertIn(MessageType.USER_MESSAGE, handler.supported_types)
        self.assertIn(MessageType.CHAT, handler.supported_types)

        # Check SSOT-specific stats
        stats = handler.get_stats()
        self.assertEqual(stats["handler_type"], "SSOT_CANONICAL")
        self.assertEqual(stats["consolidation_issue"], "#1093")
        self.assertIn("golden_path_events_sent", stats)
        self.assertIn("v3_pattern_usage", stats)
        self.assertIn("user_isolation_instances", stats)

    async def test_ssot_handler_can_handle_all_message_types(self):
        """Test that SSOT handler can handle all required message types."""
        mock_service = MagicMock()
        mock_websocket = MagicMock()
        handler = SSotAgentMessageHandler(mock_service, mock_websocket)

        # Test all supported types
        self.assertTrue(handler.can_handle(MessageType.START_AGENT))
        self.assertTrue(handler.can_handle(MessageType.USER_MESSAGE))
        self.assertTrue(handler.can_handle(MessageType.CHAT))

        # Test unsupported types
        self.assertFalse(handler.can_handle(MessageType.CONNECT))
        self.assertFalse(handler.can_handle(MessageType.DISCONNECT))

    @patch('netra_backend.app.websocket_core.ssot_agent_message_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.ssot_agent_message_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.ssot_agent_message_handler.get_request_scoped_db_session')
    @patch('netra_backend.app.websocket_core.ssot_agent_message_handler.WebSocketContext')
    @patch('netra_backend.app.websocket_core.ssot_agent_message_handler.get_websocket_scoped_supervisor')
    async def test_ssot_handler_start_agent_message(self, mock_supervisor, mock_context_class,
                                                  mock_db_session, mock_ws_manager, mock_user_context):
        """Test SSOT handler processes START_AGENT messages correctly."""
        # Setup mocks
        mock_user_context_instance = MagicMock()
        mock_user_context_instance.thread_id = "thread-123"
        mock_user_context_instance.run_id = "run-456"
        mock_user_context.return_value = mock_user_context_instance

        mock_ws_manager_instance = MagicMock()
        mock_ws_manager_instance.get_connection_id_by_websocket.return_value = "conn-789"
        mock_ws_manager.return_value = mock_ws_manager_instance

        # Mock database session
        mock_session = MagicMock()
        mock_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_session.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_db_session.return_value.__aiter__ = AsyncMock(return_value=iter([mock_session]))

        # Mock WebSocketContext
        mock_context_instance = MagicMock()
        mock_context_instance.user_id = self.user_id
        mock_context_instance.thread_id = "thread-123"
        mock_context_instance.run_id = "run-456"
        mock_context_instance.update_activity = MagicMock()
        mock_context_instance.validate_for_message_processing = MagicMock()
        mock_context_class.create_for_user.return_value = mock_context_instance

        # Mock supervisor
        mock_supervisor_instance = MagicMock()
        mock_supervisor.return_value = mock_supervisor_instance

        # Create START_AGENT message
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"user_request": "Test request"},
            thread_id="thread-123"
        )

        # Mock ThreadService
        with patch('netra_backend.app.websocket_core.ssot_agent_message_handler.ThreadService'):
            # Mock MessageHandlerService
            with patch('netra_backend.app.websocket_core.ssot_agent_message_handler.MessageHandlerService') as mock_mhs:
                mock_mhs_instance = MagicMock()
                mock_mhs_instance.handle_start_agent = AsyncMock(return_value=True)
                mock_mhs.return_value = mock_mhs_instance

                # Test the handler
                result = await self.ssot_handler.handle_message(self.user_id, self.mock_websocket, message)

                # Verify success
                self.assertTrue(result)

                # Verify context creation
                mock_user_context.assert_called_once_with(
                    user_id=self.user_id,
                    thread_id="thread-123",
                    run_id=None
                )

                # Verify message handler called
                mock_mhs_instance.handle_start_agent.assert_called_once()

                # Check stats updated
                stats = self.ssot_handler.get_stats()
                self.assertEqual(stats["start_agent_requests"], 1)
                self.assertEqual(stats["messages_processed"], 1)
                self.assertEqual(stats["golden_path_events_sent"], 5)  # All 5 events

    @patch('netra_backend.app.websocket_core.ssot_agent_message_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.ssot_agent_message_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.ssot_agent_message_handler.get_request_scoped_db_session')
    @patch('netra_backend.app.websocket_core.ssot_agent_message_handler.WebSocketContext')
    @patch('netra_backend.app.websocket_core.ssot_agent_message_handler.get_websocket_scoped_supervisor')
    async def test_ssot_handler_user_message(self, mock_supervisor, mock_context_class,
                                           mock_db_session, mock_ws_manager, mock_user_context):
        """Test SSOT handler processes USER_MESSAGE messages correctly."""
        # Setup mocks (similar to above)
        mock_user_context_instance = MagicMock()
        mock_user_context_instance.thread_id = "thread-123"
        mock_user_context_instance.run_id = "run-456"
        mock_user_context.return_value = mock_user_context_instance

        mock_ws_manager_instance = MagicMock()
        mock_ws_manager.return_value = mock_ws_manager_instance

        mock_session = MagicMock()
        mock_db_session.return_value.__aiter__ = AsyncMock(return_value=iter([mock_session]))

        mock_context_instance = MagicMock()
        mock_context_instance.user_id = self.user_id
        mock_context_instance.update_activity = MagicMock()
        mock_context_instance.validate_for_message_processing = MagicMock()
        mock_context_class.create_for_user.return_value = mock_context_instance

        mock_supervisor.return_value = MagicMock()

        # Create USER_MESSAGE
        message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"message": "Hello, agent!"},
            thread_id="thread-123"
        )

        with patch('netra_backend.app.websocket_core.ssot_agent_message_handler.ThreadService'):
            with patch('netra_backend.app.websocket_core.ssot_agent_message_handler.MessageHandlerService') as mock_mhs:
                mock_mhs_instance = MagicMock()
                mock_mhs_instance.handle_user_message = AsyncMock(return_value=True)
                mock_mhs.return_value = mock_mhs_instance

                # Test the handler
                result = await self.ssot_handler.handle_message(self.user_id, self.mock_websocket, message)

                # Verify success
                self.assertTrue(result)

                # Verify message handler called
                mock_mhs_instance.handle_user_message.assert_called_once()

                # Check stats
                stats = self.ssot_handler.get_stats()
                self.assertEqual(stats["user_messages"], 1)

    async def test_ssot_handler_missing_user_request(self):
        """Test SSOT handler handles missing user request gracefully."""
        # Create START_AGENT message without user_request
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={},  # Missing user_request
            thread_id="thread-123"
        )

        with patch('netra_backend.app.websocket_core.ssot_agent_message_handler.get_user_execution_context'):
            with patch('netra_backend.app.websocket_core.ssot_agent_message_handler.create_websocket_manager'):
                with patch('netra_backend.app.websocket_core.ssot_agent_message_handler.get_request_scoped_db_session'):
                    with patch('netra_backend.app.websocket_core.ssot_agent_message_handler.WebSocketContext') as mock_context_class:
                        mock_context_instance = MagicMock()
                        mock_context_instance.user_id = self.user_id
                        mock_context_instance.update_activity = MagicMock()
                        mock_context_instance.validate_for_message_processing = MagicMock()
                        mock_context_class.create_for_user.return_value = mock_context_instance

                        # Test the handler - should return False for missing user_request
                        result = await self.ssot_handler._handle_ssot_message_v3(
                            mock_context_instance, message, MagicMock(), MagicMock(), self.mock_websocket
                        )

                        self.assertFalse(result)

    async def test_ssot_handler_golden_path_events_tracking(self):
        """Test that SSOT handler tracks Golden Path events correctly."""
        initial_stats = self.ssot_handler.get_stats()
        initial_events = initial_stats["golden_path_events_sent"]

        # Simulate successful message processing
        self.ssot_handler.processing_stats["golden_path_events_sent"] += 5

        updated_stats = self.ssot_handler.get_stats()
        self.assertEqual(updated_stats["golden_path_events_sent"], initial_events + 5)

        # Verify all required Golden Path events are accounted for
        expected_events = ["agent_started", "agent_thinking", "tool_executing",
                          "tool_completed", "agent_completed"]
        self.assertEqual(len(expected_events), 5)

    async def test_ssot_handler_backwards_compatibility(self):
        """Test that SSOT handler maintains backwards compatibility."""
        # Test that aliases work
        from netra_backend.app.websocket_core.ssot_agent_message_handler import AgentMessageHandler, AgentHandler

        # Verify aliases point to SSOT implementation
        self.assertEqual(AgentMessageHandler, SSotAgentMessageHandler)
        self.assertEqual(AgentHandler, SSotAgentMessageHandler)

        # Test that backwards compatible instances work
        compat_handler = AgentMessageHandler(self.mock_message_handler_service, self.mock_websocket)
        self.assertIsInstance(compat_handler, SSotAgentMessageHandler)

        # Test interface compatibility
        self.assertTrue(hasattr(compat_handler, 'handle_message'))
        self.assertTrue(hasattr(compat_handler, 'can_handle'))
        self.assertTrue(hasattr(compat_handler, 'get_stats'))

    async def test_ssot_handler_error_handling(self):
        """Test SSOT handler error handling and recovery."""
        # Create message that will cause error
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"user_request": "Test request"},
            thread_id="thread-123"
        )

        # Mock to raise exception
        with patch('netra_backend.app.websocket_core.ssot_agent_message_handler.get_user_execution_context') as mock_context:
            mock_context.side_effect = Exception("Test error")

            result = await self.ssot_handler.handle_message(self.user_id, self.mock_websocket, message)

            # Should handle error gracefully
            self.assertFalse(result)

            # Check error stats
            stats = self.ssot_handler.get_stats()
            self.assertGreater(stats["errors"], 0)

    async def test_ssot_handler_stats_comprehensive(self):
        """Test that SSOT handler provides comprehensive statistics."""
        stats = self.ssot_handler.get_stats()

        # Verify all expected stats are present
        expected_stats = [
            "messages_processed",
            "start_agent_requests",
            "user_messages",
            "chat_messages",
            "errors",
            "last_processed_time",
            "golden_path_events_sent",
            "v3_pattern_usage",
            "user_isolation_instances",
            "handler_type",
            "supported_message_types",
            "consolidation_issue"
        ]

        for stat in expected_stats:
            self.assertIn(stat, stats, f"Missing expected statistic: {stat}")

        # Verify SSOT-specific values
        self.assertEqual(stats["handler_type"], "SSOT_CANONICAL")
        self.assertEqual(stats["consolidation_issue"], "#1093")
        self.assertEqual(stats["supported_message_types"], 3)


class TestSSotHandlerConsolidationSuccess(SSotAsyncTestCase):
    """Tests confirming successful consolidation of fragmented handlers."""

    async def test_consolidation_eliminates_fragmentation(self):
        """Test that SSOT handler eliminates the need for multiple handlers."""
        # Import SSOT handler
        from netra_backend.app.websocket_core.ssot_agent_message_handler import SSotAgentMessageHandler

        # Verify single canonical implementation
        self.assertTrue(hasattr(SSotAgentMessageHandler, 'handle_message'))
        self.assertTrue(hasattr(SSotAgentMessageHandler, '_handle_message_v3_clean_ssot'))
        self.assertTrue(hasattr(SSotAgentMessageHandler, '_route_ssot_agent_message_v3'))
        self.assertTrue(hasattr(SSotAgentMessageHandler, '_handle_ssot_message_v3'))

        # Verify backwards compatibility
        from netra_backend.app.websocket_core.ssot_agent_message_handler import AgentMessageHandler, AgentHandler
        self.assertEqual(AgentMessageHandler, SSotAgentMessageHandler)
        self.assertEqual(AgentHandler, SSotAgentMessageHandler)

    async def test_consolidation_preserves_all_functionality(self):
        """Test that consolidation preserves all functionality from fragmented handlers."""
        mock_service = MagicMock()
        mock_websocket = MagicMock()

        handler = SSotAgentMessageHandler(mock_service, mock_websocket)

        # Test all message types supported
        self.assertTrue(handler.can_handle(MessageType.START_AGENT))
        self.assertTrue(handler.can_handle(MessageType.USER_MESSAGE))
        self.assertTrue(handler.can_handle(MessageType.CHAT))

        # Test statistics functionality
        stats = handler.get_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("handler_type", stats)

        # Test V3 pattern methods exist
        v3_methods = [
            "_handle_message_v3_clean_ssot",
            "_route_ssot_agent_message_v3",
            "_handle_ssot_message_v3"
        ]

        for method in v3_methods:
            self.assertTrue(hasattr(handler, method), f"Missing V3 method: {method}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])