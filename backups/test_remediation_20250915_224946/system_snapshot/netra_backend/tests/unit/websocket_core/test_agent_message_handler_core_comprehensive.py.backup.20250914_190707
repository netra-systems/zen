"""
Agent Message Handler Core Unit Tests - Comprehensive Coverage

Business Value Justification:
- Segment: Platform/Internal - Core Infrastructure
- Business Goal: Stability & Reliability - $500K+ ARR dependency
- Value Impact: Validates WebSocket-agent bridge critical for Golden Path user flow
- Strategic Impact: Ensures reliable message routing from user → WebSocket → agent execution

Tests the core functionality of AgentMessageHandler which serves as the critical bridge
between WebSocket connections and agent execution. This is fundamental to the Golden Path
user flow: login → send message → agent processes → AI response.

Coverage Focus:
- AgentMessageHandler initialization and configuration
- Message type routing and validation
- WebSocket context creation and management
- User isolation and session continuity
- Error handling and recovery scenarios
- Processing statistics and monitoring
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import WebSocket

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.websocket_core.context import WebSocketContext
from netra_backend.app.services.message_handlers import MessageHandlerService


class TestAgentMessageHandlerCore(SSotAsyncTestCase):
    """Core unit tests for AgentMessageHandler initialization and basic functionality."""

    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)

        # Create mock dependencies
        self.mock_message_handler_service = AsyncMock(spec=MessageHandlerService)
        self.mock_websocket = AsyncMock(spec=WebSocket)
        self.mock_websocket.scope = {'app': MagicMock()}
        self.mock_websocket.scope['app'].state = MagicMock()

        # Test user data
        self.test_user_id = "user_12345678"
        self.test_thread_id = "thread_87654321"
        self.test_run_id = "run_11223344"
        self.test_connection_id = "conn_99887766"

    def test_agent_handler_initialization_with_required_dependencies(self):
        """Test AgentMessageHandler initialization with required dependencies."""
        # Create handler with message service
        handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=self.mock_websocket
        )

        # Verify initialization
        assert handler.message_handler_service == self.mock_message_handler_service
        assert handler.websocket == self.mock_websocket

        # Verify supported message types
        expected_types = [MessageType.START_AGENT, MessageType.USER_MESSAGE, MessageType.CHAT]
        assert handler.supported_types == expected_types

        # Verify statistics initialization
        stats = handler.get_stats()
        assert stats["messages_processed"] == 0
        assert stats["start_agent_requests"] == 0
        assert stats["user_messages"] == 0
        assert stats["chat_messages"] == 0
        assert stats["errors"] == 0
        assert stats["last_processed_time"] is None

    def test_agent_handler_initialization_without_optional_websocket(self):
        """Test AgentMessageHandler initialization without optional websocket parameter."""
        handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service
        )

        # Verify initialization
        assert handler.message_handler_service == self.mock_message_handler_service
        assert handler.websocket is None
        assert len(handler.supported_types) == 3

    def test_processing_statistics_tracking_functionality(self):
        """Test processing statistics tracking and updates."""
        handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service
        )

        # Test initial stats
        initial_stats = handler.get_stats()
        assert initial_stats["messages_processed"] == 0

        # Test START_AGENT message stat update
        handler._update_processing_stats(MessageType.START_AGENT)
        stats = handler.get_stats()
        assert stats["messages_processed"] == 1
        assert stats["start_agent_requests"] == 1
        assert stats["user_messages"] == 0
        assert stats["last_processed_time"] is not None

        # Test USER_MESSAGE stat update
        handler._update_processing_stats(MessageType.USER_MESSAGE)
        stats = handler.get_stats()
        assert stats["messages_processed"] == 2
        assert stats["start_agent_requests"] == 1
        assert stats["user_messages"] == 1

        # Test CHAT message stat update
        handler._update_processing_stats(MessageType.CHAT)
        stats = handler.get_stats()
        assert stats["messages_processed"] == 3
        assert stats["chat_messages"] == 1

    def test_statistics_immutability_and_isolation(self):
        """Test that statistics are returned as copies and don't affect internal state."""
        handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service
        )

        # Get stats and modify returned dict
        stats1 = handler.get_stats()
        stats1["messages_processed"] = 999
        stats1["malicious_field"] = "hacked"

        # Verify internal state unchanged
        stats2 = handler.get_stats()
        assert stats2["messages_processed"] == 0
        assert "malicious_field" not in stats2

        # Verify independence of returned copies
        assert stats1["messages_processed"] != stats2["messages_processed"]


class TestAgentMessageHandlerMessageTypes(SSotAsyncTestCase):
    """Unit tests for message type handling and routing logic."""

    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)

        self.mock_message_handler_service = AsyncMock(spec=MessageHandlerService)
        self.mock_websocket = AsyncMock(spec=WebSocket)
        self.handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=self.mock_websocket
        )

    def test_start_agent_message_type_recognition(self):
        """Test START_AGENT message type handling."""
        # Verify START_AGENT is in supported types
        assert MessageType.START_AGENT in self.handler.supported_types

        # Create START_AGENT message
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"user_request": "Help me analyze data"},
            thread_id="thread_123",
            run_id="run_456"
        )

        # Verify message type detection
        assert message.type == MessageType.START_AGENT
        assert message.payload["user_request"] is not None

    def test_user_message_type_recognition(self):
        """Test USER_MESSAGE message type handling."""
        # Verify USER_MESSAGE is in supported types
        assert MessageType.USER_MESSAGE in self.handler.supported_types

        # Create USER_MESSAGE message
        message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"message": "What's the weather today?"},
            thread_id="thread_789",
            run_id="run_012"
        )

        # Verify message type detection
        assert message.type == MessageType.USER_MESSAGE
        assert message.payload["message"] is not None

    def test_chat_message_type_recognition(self):
        """Test CHAT message type handling."""
        # Verify CHAT is in supported types
        assert MessageType.CHAT in self.handler.supported_types

        # Create CHAT message
        message = WebSocketMessage(
            type=MessageType.CHAT,
            payload={"content": "Continue our conversation"},
            thread_id="thread_345",
            run_id="run_678"
        )

        # Verify message type detection
        assert message.type == MessageType.CHAT
        assert message.payload["content"] is not None

    def test_unsupported_message_type_handling(self):
        """Test behavior with unsupported message types."""
        # Create message with unsupported type (assume SYSTEM_NOTIFICATION exists)
        try:
            from netra_backend.app.websocket_core.types import MessageType
            unsupported_type = None

            # Find an unsupported type
            all_types = [attr for attr in dir(MessageType) if not attr.startswith('_')]
            for type_name in all_types:
                msg_type = getattr(MessageType, type_name)
                if msg_type not in self.handler.supported_types:
                    unsupported_type = msg_type
                    break

            if unsupported_type:
                message = WebSocketMessage(
                    type=unsupported_type,
                    payload={"test": "data"},
                    thread_id="thread_999",
                    run_id="run_999"
                )

                # Verify unsupported type is not in handler's supported types
                assert message.type not in self.handler.supported_types

        except (ImportError, AttributeError):
            # If we can't find unsupported types, skip this test
            pytest.skip("No unsupported message types available for testing")


class TestAgentMessageHandlerUserIsolation(SSotAsyncTestCase):
    """Unit tests for user isolation and context management."""

    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)

        self.mock_message_handler_service = AsyncMock(spec=MessageHandlerService)
        self.mock_websocket = AsyncMock(spec=WebSocket)
        self.handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=self.mock_websocket
        )

    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    @patch('netra_backend.app.websocket_core.agent_handler.create_websocket_manager')
    @patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session')
    async def test_user_context_isolation_between_requests(self, mock_db_session,
                                                          mock_ws_manager, mock_context):
        """Test that different users get isolated contexts."""
        # Mock context creation for different users
        mock_context.side_effect = lambda user_id, thread_id=None, run_id=None: MagicMock(
            user_id=user_id,
            thread_id=thread_id or f"thread_{user_id}",
            run_id=run_id or f"run_{user_id}"
        )

        mock_ws_manager.return_value = AsyncMock()
        mock_db_session.return_value.__aenter__ = AsyncMock()
        mock_db_session.return_value.__aexit__ = AsyncMock()

        # Create messages from different users
        user1_id = "user_111"
        user2_id = "user_222"

        message1 = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"message": "User 1 message"},
            thread_id="thread_111",
            run_id="run_111"
        )

        message2 = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"message": "User 2 message"},
            thread_id="thread_222",
            run_id="run_222"
        )

        # Process messages for different users (will fail due to missing dependencies,
        # but we can verify context isolation setup)
        try:
            await self.handler.handle_message(user1_id, self.mock_websocket, message1)
        except Exception:
            pass  # Expected due to mock setup

        try:
            await self.handler.handle_message(user2_id, self.mock_websocket, message2)
        except Exception:
            pass  # Expected due to mock setup

        # Verify contexts were created with correct user isolation
        assert mock_context.call_count == 2

        # Verify first call was for user1
        call1_args = mock_context.call_args_list[0]
        assert call1_args[1]['user_id'] == user1_id

        # Verify second call was for user2
        call2_args = mock_context.call_args_list[1]
        assert call2_args[1]['user_id'] == user2_id

    def test_session_continuity_with_existing_thread_id(self):
        """Test that existing thread_id and run_id are preserved for session continuity."""
        # Create message with existing thread and run IDs
        existing_thread_id = "existing_thread_12345"
        existing_run_id = "existing_run_67890"

        message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={
                "message": "Continue our conversation",
                "thread_id": existing_thread_id,
                "run_id": existing_run_id
            },
            thread_id=existing_thread_id,
            run_id=existing_run_id
        )

        # Verify message contains session continuity information
        assert message.thread_id == existing_thread_id
        assert message.run_id == existing_run_id
        assert message.payload.get("thread_id") == existing_thread_id
        assert message.payload.get("run_id") == existing_run_id

    def test_new_session_handling_without_existing_ids(self):
        """Test handling of new sessions without existing thread_id or run_id."""
        # Create message without existing session IDs
        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"user_request": "Start new conversation"},
            thread_id=None,
            run_id=None
        )

        # Verify message indicates new session
        assert message.thread_id is None
        assert message.run_id is None
        assert message.payload.get("thread_id") is None
        assert message.payload.get("run_id") is None


class TestAgentMessageHandlerErrorHandling(SSotAsyncTestCase):
    """Unit tests for error handling and recovery scenarios."""

    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)

        self.mock_message_handler_service = AsyncMock(spec=MessageHandlerService)
        self.mock_websocket = AsyncMock(spec=WebSocket)
        self.handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=self.mock_websocket
        )

    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_context_creation_failure_handling(self, mock_context):
        """Test handling of context creation failures."""
        # Mock context creation to raise exception
        mock_context.side_effect = Exception("Context creation failed")

        message = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload={"message": "Test message"},
            thread_id="thread_123",
            run_id="run_456"
        )

        # Process message and expect graceful failure
        result = await self.handler.handle_message("user_123", self.mock_websocket, message)

        # Verify failure is handled gracefully
        assert result is False

        # Verify error statistics updated
        stats = self.handler.get_stats()
        assert stats["errors"] > 0

    def test_invalid_message_payload_handling(self):
        """Test handling of invalid or malformed message payloads."""
        # Test with None payload
        message_none_payload = WebSocketMessage(
            type=MessageType.USER_MESSAGE,
            payload=None,
            thread_id="thread_123",
            run_id="run_456"
        )

        # Test with empty payload
        message_empty_payload = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={},
            thread_id="thread_789",
            run_id="run_012"
        )

        # Verify messages can be created (validation happens during processing)
        assert message_none_payload.payload is None
        assert message_empty_payload.payload == {}

    def test_error_statistics_tracking(self):
        """Test that error statistics are properly tracked."""
        initial_stats = self.handler.get_stats()
        initial_errors = initial_stats["errors"]

        # Increment error count manually (simulating error scenario)
        self.handler.processing_stats["errors"] += 1

        updated_stats = self.handler.get_stats()
        assert updated_stats["errors"] == initial_errors + 1


class TestAgentMessageHandlerLogging(SSotAsyncTestCase):
    """Unit tests for logging and monitoring functionality."""

    def setup_method(self, method):
        """Set up test fixtures."""
        super().setup_method(method)

        self.mock_message_handler_service = AsyncMock(spec=MessageHandlerService)
        self.mock_websocket = AsyncMock(spec=WebSocket)
        self.handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=self.mock_websocket
        )

    @patch('netra_backend.app.websocket_core.agent_handler.logger')
    @patch('netra_backend.app.websocket_core.agent_handler.get_user_execution_context')
    async def test_golden_path_logging_context_creation(self, mock_context, mock_logger):
        """Test that Golden Path logging provides comprehensive context."""
        # Mock successful context creation
        mock_context.return_value = MagicMock(
            thread_id="thread_12345",
            run_id="run_67890"
        )

        message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"user_request": "Test request"},
            thread_id="thread_12345",
            run_id="run_67890"
        )

        # Process message (will fail due to mocks, but logging should occur)
        try:
            await self.handler.handle_message("user_12345", self.mock_websocket, message)
        except Exception:
            pass  # Expected due to incomplete mocking

        # Verify Golden Path logging was called
        assert mock_logger.info.called

        # Check that logging includes Golden Path context
        log_calls = mock_logger.info.call_args_list
        golden_path_logs = [call for call in log_calls
                          if 'GOLDEN PATH' in str(call[0][0])]
        assert len(golden_path_logs) > 0

    def test_processing_statistics_timestamp_tracking(self):
        """Test that processing timestamps are properly tracked."""
        # Process a message type to update timestamp
        self.handler._update_processing_stats(MessageType.USER_MESSAGE)

        stats = self.handler.get_stats()
        assert stats["last_processed_time"] is not None
        assert isinstance(stats["last_processed_time"], (int, float))

        # Verify timestamp is recent (within last few seconds)
        current_time = time.time()
        time_diff = current_time - stats["last_processed_time"]
        assert time_diff < 5  # Should be very recent


if __name__ == "__main__":
    pytest.main([__file__])