"""
Test suite for thread switching data loading functionality.
Verifies that switching threads loads and sends thread messages to the client.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from shared.isolated_environment import IsolatedEnvironment

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.db.models_postgres import Message, Thread
from netra_backend.app.services.message_handlers import MessageHandlerService
from netra_backend.app.services.thread_service import ThreadService


class TestThreadSwitchDataLoading:
    """Test thread switching with data loading"""
    
    @pytest.fixture
    async def mock_thread(self):
        """Create a mock thread"""
        thread = Mock(spec=Thread)
        thread.id = "thread_123"
        thread.metadata_ = {"user_id": "test_user", "created_at": "2025-01-01"}
        return thread
    
    @pytest.fixture
    async def mock_messages(self):
        """Create mock messages for thread"""
        messages = []
        for i in range(3):
            msg = Mock(spec=Message)
            msg.id = f"msg_{i}"
            msg.role = "user" if i % 2 == 0 else "assistant"
            msg.content = [{"text": {"value": f"Message content {i}"}}]
            msg.created_at = datetime.now()
            msg.metadata_ = {}
            messages.append(msg)
        return messages
    
    @pytest.fixture
    async def handler(self):
        """Create MessageHandlerService with mocks"""
        supervisor = supervisor_instance  # Initialize appropriate service
        thread_service = Mock(spec=ThreadService)
        websocket_manager = UnifiedWebSocketManager()
        
        handler = MessageHandlerService(
            supervisor=supervisor,
            thread_service=thread_service,
            websocket_manager=websocket_manager
        )
        return handler
    
    @pytest.mark.asyncio
    async def test_switch_thread_loads_messages(self, handler, mock_thread, mock_messages):
        """Test that switching threads loads and sends messages"""
        # Setup mocks
        handler.thread_service.get_thread = AsyncMock(return_value=mock_thread)
        handler.thread_service.get_thread_messages = AsyncMock(return_value=mock_messages)
        
        # Mock WebSocket manager
        with patch('netra_backend.app.services.message_handlers.manager') as mock_manager:
            mock_manager.send_message = AsyncNone  # TODO: Use real service instance
            mock_manager.send_error = AsyncNone  # TODO: Use real service instance
            mock_manager.broadcasting.leave_all_rooms = AsyncNone  # TODO: Use real service instance
            mock_manager.broadcasting.join_room = AsyncNone  # TODO: Use real service instance
            
            # Create mock session
            mock_session = Mock(spec=AsyncSession)
            
            # Call switch_thread
            payload = {"thread_id": "thread_123"}
            await handler.handle_switch_thread(
                user_id="test_user",
                payload=payload,
                db_session=mock_session
            )
            
            # Verify thread was validated
            handler.thread_service.get_thread.assert_called_once_with(
                "thread_123", user_id="test_user", db=mock_session
            )
            
            # Verify messages were loaded
            handler.thread_service.get_thread_messages.assert_called_once_with(
                "thread_123", db=mock_session
            )
            
            # Verify thread_data message was sent
            mock_manager.send_message.assert_called_once()
            call_args = mock_manager.send_message.call_args
            user_id_arg = call_args[0][0]
            message_arg = call_args[0][1]
            
            assert user_id_arg == "test_user"
            assert message_arg["type"] == "thread_data"
            assert message_arg["payload"]["thread_id"] == "thread_123"
            assert len(message_arg["payload"]["messages"]) == 3
            
            # Verify message format
            first_msg = message_arg["payload"]["messages"][0]
            assert first_msg["id"] == "msg_0"
            assert first_msg["role"] == "user"
            assert first_msg["content"] == "Message content 0"
            
            # Verify room operations
            mock_manager.broadcasting.leave_all_rooms.assert_called_once_with("test_user")
            mock_manager.broadcasting.join_room.assert_called_once_with("test_user", "thread_123")
    
    @pytest.mark.asyncio
    async def test_switch_thread_access_denied(self, handler, mock_thread):
        """Test that switching to unauthorized thread is denied"""
        # Setup mocks - thread has different user
        mock_thread.metadata_ = {"user_id": "other_user"}
        handler.thread_service.get_thread = AsyncMock(return_value=mock_thread)
        
        with patch('netra_backend.app.services.message_handlers.manager') as mock_manager:
            mock_manager.send_error = AsyncNone  # TODO: Use real service instance
            
            # Create mock session
            mock_session = Mock(spec=AsyncSession)
            
            # Call switch_thread
            payload = {"thread_id": "thread_123"}
            await handler.handle_switch_thread(
                user_id="test_user",
                payload=payload,
                db_session=mock_session
            )
            
            # Verify access denied error was sent
            mock_manager.send_error.assert_called_once_with(
                "test_user", "Access denied to thread"
            )
    
    @pytest.mark.asyncio
    async def test_switch_thread_no_session(self, handler):
        """Test thread switch without database session"""
        with patch('netra_backend.app.services.message_handlers.manager') as mock_manager:
            mock_manager.broadcasting.leave_all_rooms = AsyncNone  # TODO: Use real service instance
            mock_manager.broadcasting.join_room = AsyncNone  # TODO: Use real service instance
            
            # Call switch_thread without session
            payload = {"thread_id": "thread_123"}
            await handler.handle_switch_thread(
                user_id="test_user",
                payload=payload,
                db_session=None
            )
            
            # Should still perform room switch
            mock_manager.broadcasting.leave_all_rooms.assert_called_once_with("test_user")
            mock_manager.broadcasting.join_room.assert_called_once_with("test_user", "thread_123")
            
            # But no messages loaded
            handler.thread_service.get_thread_messages.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_switch_thread_message_loading_error(self, handler, mock_thread):
        """Test thread switch continues even if message loading fails"""
        # Setup mocks
        handler.thread_service.get_thread = AsyncMock(return_value=mock_thread)
        handler.thread_service.get_thread_messages = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        with patch('netra_backend.app.services.message_handlers.manager') as mock_manager:
            mock_manager.broadcasting.leave_all_rooms = AsyncNone  # TODO: Use real service instance
            mock_manager.broadcasting.join_room = AsyncNone  # TODO: Use real service instance
            
            # Create mock session
            mock_session = Mock(spec=AsyncSession)
            
            # Call switch_thread
            payload = {"thread_id": "thread_123"}
            await handler.handle_switch_thread(
                user_id="test_user",
                payload=payload,
                db_session=mock_session
            )
            
            # Should still perform room switch despite error
            mock_manager.broadcasting.leave_all_rooms.assert_called_once_with("test_user")
            mock_manager.broadcasting.join_room.assert_called_once_with("test_user", "thread_123")
    
    @pytest.mark.asyncio
    async def test_switch_thread_websocket_association(self, handler, mock_thread):
        """Test that WebSocket connection association is updated"""
        # Setup mocks
        handler.thread_service.get_thread = AsyncMock(return_value=mock_thread)
        handler.thread_service.get_thread_messages = AsyncMock(return_value=[])
        
        # Mock WebSocket
        mock_websocket = UnifiedWebSocketManager()
        handler.websocket_manager.get_connection_id_by_websocket = Mock(
            return_value="conn_456"
        )
        handler.websocket_manager.update_connection_thread = Mock(return_value=True)
        
        with patch('netra_backend.app.services.message_handlers.manager') as mock_manager:
            mock_manager.send_message = AsyncNone  # TODO: Use real service instance
            mock_manager.broadcasting.leave_all_rooms = AsyncNone  # TODO: Use real service instance
            mock_manager.broadcasting.join_room = AsyncNone  # TODO: Use real service instance
            
            # Create mock session
            mock_session = Mock(spec=AsyncSession)
            
            # Call switch_thread with websocket
            payload = {"thread_id": "thread_123"}
            await handler.handle_switch_thread(
                user_id="test_user",
                payload=payload,
                db_session=mock_session,
                websocket=mock_websocket
            )
            
            # Verify WebSocket association was updated
            handler.websocket_manager.get_connection_id_by_websocket.assert_called_once_with(
                mock_websocket
            )
            handler.websocket_manager.update_connection_thread.assert_called_once_with(
                "conn_456", "thread_123"
            )
    
    @pytest.mark.asyncio
    async def test_format_message_for_client(self, handler):
        """Test message formatting for client"""
        # Create a message with the expected structure
        msg = Mock(spec=Message)
        msg.id = "msg_1"
        msg.role = "user"
        msg.content = [{"text": {"value": "Hello, world!"}}]
        msg.created_at = datetime(2025, 1, 1, 12, 0, 0)
        msg.metadata_ = {"key": "value"}
        
        # Format the message
        formatted = handler._format_message_for_client(msg)
        
        # Verify format
        assert formatted["id"] == "msg_1"
        assert formatted["role"] == "user"
        assert formatted["content"] == "Hello, world!"
        assert formatted["timestamp"] == datetime(2025, 1, 1, 12, 0, 0)
        assert formatted["metadata"] == {"key": "value"}
    
    @pytest.mark.asyncio
    async def test_format_message_with_empty_content(self, handler):
        """Test formatting message with empty or malformed content"""
        # Test with empty content
        msg = Mock(spec=Message)
        msg.id = "msg_1"
        msg.role = "user"
        msg.content = []
        msg.created_at = None
        
        formatted = handler._format_message_for_client(msg)
        assert formatted["content"] == ""
        
        # Test with None content
        msg.content = None
        formatted = handler._format_message_for_client(msg)
        assert formatted["content"] == ""
        
        # Test with malformed content
        msg.content = [{"wrong": "format"}]
        formatted = handler._format_message_for_client(msg)
        assert formatted["content"] == ""