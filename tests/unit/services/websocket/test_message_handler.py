"""
Unit Tests for WebSocket Message Handler

Tests user message serialization/deserialization, agent message validation,
message type routing, concurrent message handling, and error recovery.

Business Value: Platform/Internal - Testing Infrastructure
Ensures reliable message handling for Golden Path chat functionality.
"""

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from test_framework.ssot.mock_factory import SSotMockFactory
from netra_backend.app.websocket_core.types import (
    WebSocketMessage, MessageType, create_standard_message,
    serialize_message_safely, normalize_message_type
)
from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.services.message_handlers import MessageHandlerService


class TestWebSocketMessageHandler(SSotAsyncTestCase):
    """Test WebSocket message handler functionality with SSOT patterns."""

    def setup_method(self, method):
        """Setup test environment for each test."""
        super().setup_method(method)
        
        # Create mock dependencies using SSOT factory
        self.mock_message_handler_service = SSotMockFactory.create_mock(
            "MessageHandlerService"
        )
        self.mock_websocket = SSotMockFactory.create_websocket_mock()
        
        # Create agent message handler instance
        self.agent_handler = AgentMessageHandler(
            message_handler_service=self.mock_message_handler_service,
            websocket=self.mock_websocket
        )
        
        # Test data
        self.user_id = "test_user_123"
        self.thread_id = "thread_456"
        self.connection_id = "conn_789"

    async def test_user_message_serialization_valid_data(self):
        """Test successful user message serialization with valid data."""
        # Arrange
        message_data = {
            "message": "Hello, how can I help you today?",
            "context": "greeting",
            "metadata": {"source": "frontend"}
        }
        
        # Act
        message = create_standard_message(
            msg_type=MessageType.USER_MESSAGE,
            payload=message_data,
            user_id=self.user_id,
            thread_id=self.thread_id
        )
        
        # Assert
        self.assertEqual(message.type, MessageType.USER_MESSAGE)
        self.assertEqual(message.payload, message_data)
        self.assertEqual(message.user_id, self.user_id)
        self.assertEqual(message.thread_id, self.thread_id)
        self.assertIsNotNone(message.message_id)
        self.assertIsNotNone(message.timestamp)
        
        # Verify serialization
        serialized = serialize_message_safely(message)
        self.assertIsInstance(serialized, dict)
        self.assertIn('type', serialized)
        self.assertIn('payload', serialized)

    async def test_user_message_deserialization_from_json(self):
        """Test message deserialization from JSON with proper validation."""
        # Arrange
        json_data = {
            "type": "user_message",
            "payload": {
                "message": "Test message content",
                "thread_id": self.thread_id
            },
            "user_id": self.user_id,
            "timestamp": time.time()
        }
        
        # Act
        message = WebSocketMessage(**json_data)
        
        # Assert
        self.assertEqual(message.type, MessageType.USER_MESSAGE)
        self.assertEqual(message.payload["message"], "Test message content")
        self.assertEqual(message.user_id, self.user_id)
        self.assertIsNotNone(message.timestamp)

    async def test_agent_message_validation_required_fields(self):
        """Test agent message validation ensures required fields are present."""
        # Test missing user_request field
        invalid_payload = {
            "agent_type": "triage",
            "context": "test"
        }
        
        message = create_standard_message(
            msg_type=MessageType.START_AGENT,
            payload=invalid_payload,
            user_id=self.user_id
        )
        
        # Act & Assert - should not raise exception during creation
        # but validation should happen during handling
        self.assertEqual(message.type, MessageType.START_AGENT)
        self.assertEqual(message.payload, invalid_payload)

    async def test_agent_message_validation_with_user_request(self):
        """Test agent message validation with proper user_request field."""
        # Arrange
        valid_payload = {
            "user_request": "Analyze this data for insights",
            "agent_type": "apex_optimizer",
            "context": {"analysis_type": "performance"}
        }
        
        # Act
        message = create_standard_message(
            msg_type=MessageType.START_AGENT,
            payload=valid_payload,
            user_id=self.user_id
        )
        
        # Assert
        self.assertEqual(message.type, MessageType.START_AGENT)
        self.assertEqual(message.payload["user_request"], "Analyze this data for insights")
        self.assertEqual(message.payload["agent_type"], "apex_optimizer")

    async def test_message_type_routing_start_agent(self):
        """Test message routing for START_AGENT message type."""
        # Arrange
        message = create_standard_message(
            msg_type=MessageType.START_AGENT,
            payload={"user_request": "Test agent request"},
            user_id=self.user_id
        )
        
        # Mock the handler methods
        self.mock_message_handler_service.handle_start_agent = AsyncMock(return_value=True)
        
        # Act
        with patch('netra_backend.app.dependencies.get_user_execution_context') as mock_context, \
             patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db:
            
            # Setup mocks
            mock_context.return_value = SSotMockFactory.create_mock_user_context(
                user_id=self.user_id, thread_id=self.thread_id
            )
            
            # Create async generator for database session
            async def mock_db_session():
                yield SSotMockFactory.create_database_session_mock()
            mock_db.return_value = mock_db_session()
            
            # Execute handler
            result = await self.agent_handler.handle_message(
                user_id=self.user_id,
                websocket=self.mock_websocket,
                message=message
            )
        
        # Assert
        self.assertTrue(result)
        self.mock_message_handler_service.handle_start_agent.assert_called_once()

    async def test_message_type_routing_user_message(self):
        """Test message routing for USER_MESSAGE message type."""
        # Arrange
        message = create_standard_message(
            msg_type=MessageType.USER_MESSAGE,
            payload={"message": "Hello, I need help"},
            user_id=self.user_id
        )
        
        # Mock the handler methods
        self.mock_message_handler_service.handle_user_message = AsyncMock(return_value=True)
        
        # Act
        with patch('netra_backend.app.dependencies.get_user_execution_context') as mock_context, \
             patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db:
            
            # Setup mocks
            mock_context.return_value = SSotMockFactory.create_mock_user_context(
                user_id=self.user_id, thread_id=self.thread_id
            )
            
            # Create async generator for database session
            async def mock_db_session():
                yield SSotMockFactory.create_database_session_mock()
            mock_db.return_value = mock_db_session()
            
            # Execute handler
            result = await self.agent_handler.handle_message(
                user_id=self.user_id,
                websocket=self.mock_websocket,
                message=message
            )
        
        # Assert
        self.assertTrue(result)
        self.mock_message_handler_service.handle_user_message.assert_called_once()

    async def test_message_type_routing_unknown_type(self):
        """Test message routing handles unknown message types gracefully."""
        # Arrange - create a message with unsupported type
        message = WebSocketMessage(
            type=MessageType.HEARTBEAT,  # Not handled by AgentMessageHandler
            payload={"ping": "test"},
            user_id=self.user_id
        )
        
        # Act & Assert
        with patch('netra_backend.app.dependencies.get_user_execution_context') as mock_context, \
             patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db:
            
            # Setup mocks
            mock_context.return_value = SSotMockFactory.create_mock_user_context(
                user_id=self.user_id, thread_id=self.thread_id
            )
            
            # Create async generator for database session
            async def mock_db_session():
                yield SSotMockFactory.create_database_session_mock()
            mock_db.return_value = mock_db_session()
            
            # Execute handler - should return False for unsupported types
            result = await self.agent_handler.handle_message(
                user_id=self.user_id,
                websocket=self.mock_websocket,
                message=message
            )
        
        # Assert - should return False for unsupported message type
        self.assertFalse(result)

    async def test_concurrent_message_handling_no_interference(self):
        """Test concurrent message handling without interference between requests."""
        # Arrange
        messages = []
        for i in range(5):
            message = create_standard_message(
                msg_type=MessageType.USER_MESSAGE,
                payload={"message": f"Message {i}"},
                user_id=f"user_{i}"
            )
            messages.append((f"user_{i}", message))
        
        # Mock the handler method to simulate processing time
        async def mock_handle_user_message(*args, **kwargs):
            await asyncio.sleep(0.1)  # Simulate processing time
            return True
        
        self.mock_message_handler_service.handle_user_message = AsyncMock(
            side_effect=mock_handle_user_message
        )
        
        # Act - process messages concurrently
        with patch('netra_backend.app.dependencies.get_user_execution_context') as mock_context, \
             patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db:
            
            # Setup mocks for each user
            mock_context.side_effect = lambda user_id, **kwargs: SSotMockFactory.create_mock_user_context(
                user_id=user_id, thread_id=f"thread_{user_id}"
            )
            
            # Create async generator for database session
            async def mock_db_session():
                yield SSotMockFactory.create_database_session_mock()
            mock_db.return_value = mock_db_session()
            
            # Execute all handlers concurrently
            tasks = []
            for user_id, message in messages:
                task = asyncio.create_task(
                    self.agent_handler.handle_message(
                        user_id=user_id,
                        websocket=self.mock_websocket,
                        message=message
                    )
                )
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
        
        # Assert
        self.assertTrue(all(results))
        self.assertEqual(self.mock_message_handler_service.handle_user_message.call_count, 5)

    async def test_error_recovery_in_message_processing(self):
        """Test error recovery when message processing fails."""
        # Arrange
        message = create_standard_message(
            msg_type=MessageType.START_AGENT,
            payload={"user_request": "Test request"},
            user_id=self.user_id
        )
        
        # Mock handler to raise exception
        self.mock_message_handler_service.handle_start_agent = AsyncMock(
            side_effect=Exception("Simulated processing error")
        )
        
        # Act
        with patch('netra_backend.app.dependencies.get_user_execution_context') as mock_context, \
             patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db:
            
            # Setup mocks
            mock_context.return_value = SSotMockFactory.create_mock_user_context(
                user_id=self.user_id, thread_id=self.thread_id
            )
            
            # Create async generator for database session
            async def mock_db_session():
                yield SSotMockFactory.create_database_session_mock()
            mock_db.return_value = mock_db_session()
            
            # Execute handler - should handle exception gracefully
            result = await self.agent_handler.handle_message(
                user_id=self.user_id,
                websocket=self.mock_websocket,
                message=message
            )
        
        # Assert
        self.assertFalse(result)  # Should return False on error
        
        # Verify error statistics were updated
        stats = self.agent_handler.get_stats()
        self.assertGreater(stats["errors"], 0)

    async def test_message_serialization_with_complex_payload(self):
        """Test message serialization with complex nested payload data."""
        # Arrange
        complex_payload = {
            "nested_data": {
                "list_items": [1, 2, {"inner": "value"}],
                "datetime": datetime.now(timezone.utc),
                "metadata": {
                    "tags": ["urgent", "analysis"],
                    "config": {"timeout": 30, "retry": True}
                }
            },
            "user_request": "Complex analysis request"
        }
        
        # Act
        message = create_standard_message(
            msg_type=MessageType.START_AGENT,
            payload=complex_payload,
            user_id=self.user_id
        )
        
        serialized = serialize_message_safely(message)
        
        # Assert
        self.assertIsInstance(serialized, dict)
        self.assertEqual(serialized['user_id'], self.user_id)
        self.assertIsInstance(serialized['payload'], dict)
        
        # Verify complex data was properly serialized
        payload_data = serialized['payload']
        self.assertIn('nested_data', payload_data)
        self.assertIn('user_request', payload_data)
        
        # Test JSON serialization
        json_str = json.dumps(serialized)
        self.assertIsInstance(json_str, str)

    async def test_message_type_normalization_edge_cases(self):
        """Test message type normalization handles various input formats."""
        # Test different input formats
        test_cases = [
            ("user_message", MessageType.USER_MESSAGE),
            ("USER_MESSAGE", MessageType.USER_MESSAGE),
            ("start_agent", MessageType.START_AGENT),
            ("agent_started", MessageType.AGENT_STARTED),
            (MessageType.CHAT, MessageType.CHAT),
        ]
        
        for input_type, expected_type in test_cases:
            with self.subTest(input_type=input_type):
                # Act
                normalized = normalize_message_type(input_type)
                
                # Assert
                self.assertEqual(normalized, expected_type)

    async def test_handler_statistics_tracking(self):
        """Test that handler correctly tracks processing statistics."""
        # Arrange
        initial_stats = self.agent_handler.get_stats()
        
        message = create_standard_message(
            msg_type=MessageType.USER_MESSAGE,
            payload={"message": "Test message"},
            user_id=self.user_id
        )
        
        self.mock_message_handler_service.handle_user_message = AsyncMock(return_value=True)
        
        # Act
        with patch('netra_backend.app.dependencies.get_user_execution_context') as mock_context, \
             patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db:
            
            # Setup mocks
            mock_context.return_value = SSotMockFactory.create_mock_user_context(
                user_id=self.user_id, thread_id=self.thread_id
            )
            
            # Create async generator for database session
            async def mock_db_session():
                yield SSotMockFactory.create_database_session_mock()
            mock_db.return_value = mock_db_session()
            
            # Execute handler
            await self.agent_handler.handle_message(
                user_id=self.user_id,
                websocket=self.mock_websocket,
                message=message
            )
        
        # Assert
        final_stats = self.agent_handler.get_stats()
        self.assertEqual(
            final_stats["messages_processed"],
            initial_stats["messages_processed"] + 1
        )
        self.assertEqual(
            final_stats["user_messages"],
            initial_stats["user_messages"] + 1
        )
        self.assertIsNotNone(final_stats["last_processed_time"])

    async def test_invalid_message_handling(self):
        """Test handling of invalid message formats."""
        # Test with missing required fields
        with self.assertRaises(ValueError):
            create_standard_message(
                msg_type=None,  # Missing required type
                payload={"test": "data"}
            )
        
        # Test with invalid payload type
        with self.assertRaises(TypeError):
            create_standard_message(
                msg_type=MessageType.USER_MESSAGE,
                payload="invalid_payload_type"  # Should be dict
            )

    async def test_websocket_context_creation_and_validation(self):
        """Test WebSocket context creation and validation during message handling."""
        # Arrange
        message = create_standard_message(
            msg_type=MessageType.CHAT,
            payload={"message": "Test chat message"},
            user_id=self.user_id,
            thread_id=self.thread_id
        )
        
        self.mock_message_handler_service.handle_user_message = AsyncMock(return_value=True)
        
        # Act
        with patch('netra_backend.app.dependencies.get_user_execution_context') as mock_context, \
             patch('netra_backend.app.dependencies.get_request_scoped_db_session') as mock_db, \
             patch('netra_backend.app.websocket_core.context.WebSocketContext.create_for_user') as mock_ws_context:
            
            # Setup mocks
            mock_execution_context = SSotMockFactory.create_mock_user_context(
                user_id=self.user_id, thread_id=self.thread_id
            )
            mock_context.return_value = mock_execution_context
            
            mock_websocket_context = MagicMock()
            mock_websocket_context.user_id = self.user_id
            mock_websocket_context.thread_id = self.thread_id
            mock_websocket_context.update_activity = MagicMock()
            mock_websocket_context.validate_for_message_processing = MagicMock()
            mock_ws_context.return_value = mock_websocket_context
            
            # Create async generator for database session
            async def mock_db_session():
                yield SSotMockFactory.create_database_session_mock()
            mock_db.return_value = mock_db_session()
            
            # Execute handler
            result = await self.agent_handler.handle_message(
                user_id=self.user_id,
                websocket=self.mock_websocket,
                message=message
            )
        
        # Assert
        self.assertTrue(result)
        mock_ws_context.assert_called_once()
        mock_websocket_context.update_activity.assert_called_once()
        mock_websocket_context.validate_for_message_processing.assert_called_once()