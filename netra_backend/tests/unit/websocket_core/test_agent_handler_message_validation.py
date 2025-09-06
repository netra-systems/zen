from unittest.mock import Mock, AsyncMock, patch, MagicMock
"""
Unit Tests for WebSocket Agent Handler - Message Validation Tests (7-12)

Business Value: Validates message processing and payload extraction logic
critical for reliable agent communication.
"""

import asyncio
import uuid
import json
import time
from typing import Dict, Any, Optional
from datetime import datetime
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

import pytest
import pytest_asyncio
from fastapi import WebSocket

from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage
from netra_backend.app.services.message_handlers import MessageHandlerService


# ============================================================================
# TESTS 7-12: MESSAGE HANDLING AND VALIDATION
# ============================================================================

@pytest.mark.asyncio
class TestMessageHandling:
    """Test suite for message handling, validation, and routing."""

    @pytest.fixture(autouse=True)
    def setup_mocks(self):
        """Use real service instance."""
    # TODO: Initialize real service
        """Setup common mocks for all tests."""
        pass
        self.mock_websocket = AsyncMock(spec=WebSocket)
        self.mock_db_session = AsyncNone  # TODO: Use real service instance
        self.mock_message_handler_service = AsyncMock(spec=MessageHandlerService)
        self.mock_websocket_manager = AsyncNone  # TODO: Use real service instance
        self.mock_websocket_manager.get_connection_id_by_websocket = Mock(return_value="conn-123")
        self.mock_websocket_manager.update_connection_thread = AsyncNone  # TODO: Use real service instance
        self.mock_websocket_manager.send_error = AsyncNone  # TODO: Use real service instance

        async def test_message_type_routing_all_types(self):
            """
            Test 7: Verify correct routing for all message types (START_AGENT, USER_MESSAGE, CHAT).

            Business Impact: Ensures all message types are processed correctly.
            """
            pass
            with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=self.mock_websocket_manager):
                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                    with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock):
                        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):
                            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as MockMHS:
                                pass

                            # Setup
                                async def db_generator():
                                    pass
                                    yield self.mock_db_session
                                    mock_get_db.return_value = db_generator()

                            # Track which handler methods are called
                                    mock_handler_instance = AsyncNone  # TODO: Use real service instance
                                    MockMHS.return_value = mock_handler_instance

                                    handler = AgentMessageHandler(self.mock_message_handler_service, self.mock_websocket)

                            # Test START_AGENT routing
                                    start_message = WebSocketMessage(
                                    type=MessageType.START_AGENT,
                                    payload={"user_request": "Start test"},
                                    thread_id="thread-1",
                                    timestamp=time.time()
                                    )

                                    await handler.handle_message("user1", self.mock_websocket, start_message)

                            # Verify START_AGENT was routed correctly
                                    assert mock_handler_instance.handle_start_agent.called

                            # Test USER_MESSAGE routing
                                    user_message = WebSocketMessage(
                                    type=MessageType.USER_MESSAGE,
                                    payload={"message": "User test"},
                                    thread_id="thread-2",
                                    timestamp=time.time()
                                    )

                                    await handler.handle_message("user2", self.mock_websocket, user_message)

                            # Verify USER_MESSAGE was routed correctly
                                    assert mock_handler_instance.handle_user_message.called

                            # Test CHAT routing
                                    chat_message = WebSocketMessage(
                                    type=MessageType.CHAT,
                                    payload={"content": "Chat test"},
                                    thread_id="thread-3",
                                    timestamp=time.time()
                                    )

                                    await handler.handle_message("user3", self.mock_websocket, chat_message)

                            # Verify CHAT was routed correctly (should use handle_user_message)
                                    assert mock_handler_instance.handle_user_message.call_count >= 2

                                    async def test_websocket_manager_integration_complete(self):
                                        """
                                        Test 8: Verify complete WebSocket manager integration.

                                        Business Impact: Ensures WebSocket events are properly managed.
                                        """
                                        pass
                                        with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=self.mock_websocket_manager):
                                            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                                                with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock):
                                                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):
                                                        pass

                                                        async def db_generator():
                                                            pass
                                                            yield self.mock_db_session
                                                            mock_get_db.return_value = db_generator()

                                                            handler = AgentMessageHandler(self.mock_message_handler_service, self.mock_websocket)

                        # Test WebSocket manager retrieval and usage
                                                            message = WebSocketMessage(
                                                            type=MessageType.START_AGENT,
                                                            payload={"user_request": "Test", "thread_id": "thread-test"},
                                                            thread_id="thread-test",
                                                            timestamp=datetime.utcnow().isoformat()
                                                            )

                                                            await handler.handle_message("user-test", self.mock_websocket, message)

                        # Verify WebSocket manager operations
                                                            self.mock_websocket_manager.get_connection_id_by_websocket.assert_called_with(self.mock_websocket)
                                                            self.mock_websocket_manager.update_connection_thread.assert_called_with("conn-123", "thread-test")

                        # Test error notification through WebSocket manager
                                                            with patch.object(self.mock_message_handler_service, 'handle_start_agent', side_effect=Exception("Test error")):
                                                                error_message = WebSocketMessage(
                                                                type=MessageType.START_AGENT,
                                                                payload={"user_request": "Error test"},
                                                                thread_id="thread-error",
                                                                timestamp=time.time()
                                                                )

                                                                await handler.handle_message("user-error", self.mock_websocket, error_message)

                            # Verify error was sent through WebSocket manager
                                                                self.mock_websocket_manager.send_error.assert_called()

                                                                async def test_connection_id_management_consistency(self):
                                                                    """
                                                                    Test 9: Verify consistent connection ID management.

                                                                    Business Impact: Ensures messages route to correct WebSocket connections.
                                                                    """
                                                                    pass
                                                                    connection_scenarios = [
                                                                    ("conn-found-123", True),  # Connection found
                                                                    (None, False),  # Connection not found
                                                                    ]

                                                                    for connection_id, should_update_thread in connection_scenarios:
                                                                        self.mock_websocket_manager.get_connection_id_by_websocket.return_value = connection_id
                                                                        self.mock_websocket_manager.update_connection_thread.reset_mock()

                                                                        with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=self.mock_websocket_manager):
                                                                            with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                                                                                with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock) as mock_create_context:
                                                                                    with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):
                                                                                        pass

                                                                                        async def db_generator():
                                                                                            pass
                                                                                            yield self.mock_db_session
                                                                                            mock_get_db.return_value = db_generator()

                                                                                            handler = AgentMessageHandler(self.mock_message_handler_service, self.mock_websocket)

                                                                                            message = WebSocketMessage(
                                                                                            type=MessageType.START_AGENT,
                                                                                            payload={"user_request": "Test", "thread_id": "thread-123"},
                                                                                            thread_id="thread-123",
                                                                                            timestamp=time.time()
                                                                                            )

                                                                                            await handler.handle_message("user-test", self.mock_websocket, message)

                            # Verify connection ID handling
                                                                                            if should_update_thread:
                                                                                                self.mock_websocket_manager.update_connection_thread.assert_called_with(connection_id, "thread-123")
                                # Verify connection ID passed to context
                                                                                                call_kwargs = mock_create_context.call_args[1]
                                                                                                assert call_kwargs.get('websocket_connection_id') == connection_id
                                                                                            else:
                                                                                                self.mock_websocket_manager.update_connection_thread.assert_not_called()
                                # Verify None passed when no connection ID
                                                                                                call_kwargs = mock_create_context.call_args[1]
                                                                                                assert call_kwargs.get('websocket_connection_id') is None

                                                                                                async def test_fallback_error_notifications(self):
                                                                                                    """
                                                                                                    Test 10: Verify fallback error notifications to users.

                                                                                                    Business Impact: Ensures users receive feedback even during failures.
                                                                                                    """
                                                                                                    pass
                                                                                                    with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=self.mock_websocket_manager):
                                                                                                        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                                                                                                            with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock):
                                                                                                                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):
                                                                                                                    pass

                                                                                                                    async def db_generator():
                                                                                                                        pass
                                                                                                                        yield self.mock_db_session
                                                                                                                        mock_get_db.return_value = db_generator()

                                                                                                                        handler = AgentMessageHandler(self.mock_message_handler_service, self.mock_websocket)

                        # Simulate different error scenarios
                                                                                                                        error_scenarios = [
                                                                                                                        (Exception("Generic error"), "Failed to process"),
                                                                                                                        (ImportError("Module not found"), "Failed to process"),
                                                                                                                        (RuntimeError("Runtime issue"), "Failed to process"),
                                                                                                                        ]

                                                                                                                        for error, expected_msg_part in error_scenarios:
                                                                                                                            self.mock_websocket_manager.send_error.reset_mock()

                                                                                                                            with patch.object(self.mock_message_handler_service, 'handle_start_agent', side_effect=error):
                                                                                                                                message = WebSocketMessage(
                                                                                                                                type=MessageType.START_AGENT,
                                                                                                                                payload={"user_request": "Test"},
                                                                                                                                thread_id="thread-error",
                                                                                                                                timestamp=time.time()
                                                                                                                                )

                                                                                                                                result = await handler.handle_message("user-error", self.mock_websocket, message)

                                # Verify error handling
                                                                                                                                assert result is False

                                # Verify error notification attempted
                                                                                                                                if self.mock_websocket_manager.send_error.called:
                                                                                                                                    error_call = self.mock_websocket_manager.send_error.call_args
                                                                                                                                    assert error_call[0][0] == "user-error"  # User ID
                                                                                                                                    assert expected_msg_part in error_call[0][1]  # Error message

                        # Test error notification failure doesn't break flow'
                                                                                                                                    self.mock_websocket_manager.send_error.side_effect = Exception("Notification failed")

                                                                                                                                    with patch.object(self.mock_message_handler_service, 'handle_start_agent', side_effect=Exception("Main error")):
                                                                                                                                        message = WebSocketMessage(
                                                                                                                                        type=MessageType.START_AGENT,
                                                                                                                                        payload={"user_request": "Test"},
                                                                                                                                        thread_id="thread-notify-fail",
                                                                                                                                        timestamp=time.time()
                                                                                                                                        )

                            # Should complete without raising notification error
                                                                                                                                        result = await handler.handle_message("user-notify-fail", self.mock_websocket, message)
                                                                                                                                        assert result is False  # Main error still causes failure

                                                                                                                                        async def test_payload_validation_start_agent(self):
                                                                                                                                            """
                                                                                                                                            Test 11: Verify payload validation for START_AGENT messages.

                                                                                                                                            Business Impact: Prevents processing of malformed requests.
                                                                                                                                            """
                                                                                                                                            pass
                                                                                                                                            with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=self.mock_websocket_manager):
                                                                                                                                                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                                                                                                                                                    with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock):
                                                                                                                                                        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):
                                                                                                                                                            pass

                                                                                                                                                            async def db_generator():
                                                                                                                                                                pass
                                                                                                                                                                yield self.mock_db_session
                                                                                                                                                                mock_get_db.return_value = db_generator()

                                                                                                                                                                handler = AgentMessageHandler(self.mock_message_handler_service, self.mock_websocket)

                        # Test valid payload
                                                                                                                                                                valid_message = WebSocketMessage(
                                                                                                                                                                type=MessageType.START_AGENT,
                                                                                                                                                                payload={"user_request": "Valid request", "thread_id": "thread-1"},
                                                                                                                                                                thread_id="thread-1",
                                                                                                                                                                timestamp=datetime.utcnow().isoformat()
                                                                                                                                                                )

                                                                                                                                                                result = await handler.handle_message("user-valid", self.mock_websocket, valid_message)
                                                                                                                                                                assert result is True

                        # Test missing user_request
                                                                                                                                                                invalid_message = WebSocketMessage(
                                                                                                                                                                type=MessageType.START_AGENT,
                                                                                                                                                                payload={"thread_id": "thread-2"},  # Missing user_request
                                                                                                                                                                thread_id="thread-2",
                                                                                                                                                                timestamp=datetime.utcnow().isoformat()
                                                                                                                                                                )

                                                                                                                                                                result = await handler.handle_message("user-invalid", self.mock_websocket, invalid_message)
                                                                                                                                                                assert result is False

                        # Test empty user_request
                                                                                                                                                                empty_message = WebSocketMessage(
                                                                                                                                                                type=MessageType.START_AGENT,
                                                                                                                                                                payload={"user_request": "", "thread_id": "thread-3"},
                                                                                                                                                                thread_id="thread-3",
                                                                                                                                                                timestamp=datetime.utcnow().isoformat()
                                                                                                                                                                )

                                                                                                                                                                result = await handler.handle_message("user-empty", self.mock_websocket, empty_message)
                        # Empty string might be considered valid, depends on implementation

                        # Test null user_request
                                                                                                                                                                null_message = WebSocketMessage(
                                                                                                                                                                type=MessageType.START_AGENT,
                                                                                                                                                                payload={"user_request": None, "thread_id": "thread-4"},
                                                                                                                                                                thread_id="thread-4",
                                                                                                                                                                timestamp=datetime.utcnow().isoformat()
                                                                                                                                                                )

                                                                                                                                                                result = await handler.handle_message("user-null", self.mock_websocket, null_message)
                                                                                                                                                                assert result is False

                                                                                                                                                                async def test_payload_validation_user_message_chat(self):
                                                                                                                                                                    """
                                                                                                                                                                    Test 12: Verify payload validation for USER_MESSAGE and CHAT messages.

                                                                                                                                                                    Business Impact: Ensures message content is properly extracted and validated.
                                                                                                                                                                    """
                                                                                                                                                                    pass
                                                                                                                                                                    with patch('netra_backend.app.websocket_core.get_websocket_manager', return_value=self.mock_websocket_manager):
                                                                                                                                                                        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_get_db:
                                                                                                                                                                            with patch('netra_backend.app.websocket_core.agent_handler.create_user_execution_context', new_callable=Mock):
                                                                                                                                                                                with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_supervisor', new_callable=AsyncMock):
                                                                                                                                                                                    with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as MockMHS:
                                                                                                                                                                                        pass

                                                                                                                                                                                        async def db_generator():
                                                                                                                                                                                            pass
                                                                                                                                                                                            yield self.mock_db_session
                                                                                                                                                                                            mock_get_db.return_value = db_generator()

                                                                                                                                                                                            mock_handler_instance = AsyncNone  # TODO: Use real service instance
                                                                                                                                                                                            MockMHS.return_value = mock_handler_instance

                                                                                                                                                                                            handler = AgentMessageHandler(self.mock_message_handler_service, self.mock_websocket)

                            # Test field precedence: message > content > text
                                                                                                                                                                                            test_cases = [
                                                                                                                                                                                            ({"message": "From message field"}, True),
                                                                                                                                                                                            ({"content": "From content field"}, True),
                                                                                                                                                                                            ({"text": "From text field"}, True),
                                                                                                                                                                                            ({"message": "Priority", "content": "Lower", "text": "Lowest"}, True),
                                                                                                                                                                                            ({"message": "", "content": "Backup content"}, True),
                                                                                                                                                                                            ({"message": "   ", "content": "Trimmed"}, True),
                                                                                                                                                                                            ({}, False),  # No content fields
                                                                                                                                                                                            ({"message": "", "content": "", "text": ""}, False),  # All empty
                                                                                                                                                                                            ({"message": None, "content": None, "text": None}, False),  # All null
                                                                                                                                                                                            ]

                                                                                                                                                                                            for payload, should_succeed in test_cases:
                                                                                                                                                                                                mock_handler_instance.handle_user_message.reset_mock()

                                # Test with USER_MESSAGE
                                                                                                                                                                                                user_msg = WebSocketMessage(
                                                                                                                                                                                                type=MessageType.USER_MESSAGE,
                                                                                                                                                                                                payload=payload,
                                                                                                                                                                                                thread_id=f"thread-user-{uuid.uuid4()}",
                                                                                                                                                                                                timestamp=time.time()
                                                                                                                                                                                                )

                                                                                                                                                                                                result = await handler.handle_message("test-user", self.mock_websocket, user_msg)

                                                                                                                                                                                                if should_succeed:
                                                                                                                                                                                                    assert mock_handler_instance.handle_user_message.called
                                                                                                                                                                                                else:
                                                                                                                                                                                                    assert result is False

                                # Test with CHAT
                                                                                                                                                                                                    chat_msg = WebSocketMessage(
                                                                                                                                                                                                    type=MessageType.CHAT,
                                                                                                                                                                                                    payload=payload,
                                                                                                                                                                                                    thread_id=f"thread-chat-{uuid.uuid4()}",
                                                                                                                                                                                                    timestamp=time.time()
                                                                                                                                                                                                    )

                                                                                                                                                                                                    result = await handler.handle_message("test-user", self.mock_websocket, chat_msg)

                                                                                                                                                                                                    if should_succeed:
                                    # CHAT should also call handle_user_message
                                                                                                                                                                                                        assert mock_handler_instance.handle_user_message.call_count >= 1
                                                                                                                                                                                                    else:
                                                                                                                                                                                                        assert result is False