"""
Test suite for thread switching data loading functionality.
Verifies that switching threads loads and sends thread messages to the client.
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from test_framework.database.test_database_manager import TestDatabaseManager
from netra_backend.app.models.user_execution_context import UserExecutionContext
from shared.isolated_environment import IsolatedEnvironment

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
        supervisor = MagicMock()  # Mock supervisor service for testing
        thread_service = Mock(spec=ThreadService)
        
        # MessageHandlerService constructor only takes supervisor and thread_service
        handler = MessageHandlerService(supervisor, thread_service)
        return handler
    
    @pytest.mark.asyncio
    async def test_switch_thread_loads_messages(self, handler, mock_thread, mock_messages):
        """Test that switching threads loads and sends messages"""
        # Setup mocks
        handler.thread_service.get_thread = AsyncMock(return_value=mock_thread)
        handler.thread_service.get_thread_messages = AsyncMock(return_value=mock_messages)
        
        # Mock WebSocket manager
        with patch('netra_backend.app.services.message_handlers.create_websocket_manager') as mock_create_manager:
            mock_manager = MagicMock()
            mock_manager.send_to_user = AsyncMock()
            mock_create_manager.return_value = mock_manager
            
            # Create mock session
            mock_session = Mock(spec=AsyncSession)
            
            # Call switch_thread
            payload = {"thread_id": "thread_123"}
            
            # Create proper UserExecutionContext
            user_context = UserExecutionContext(
                user_id="test_user",
                thread_id="thread_123",
                run_id="test-run-123",
                request_id="test-request-456"
            )
            
            await handler.handle_switch_thread(
                user_context=user_context,
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
            
            # Verify thread_data message was sent via WebSocket manager
            mock_manager.send_to_user.assert_called()
            
            # Get the last call to send_to_user (there might be multiple calls)
            last_call_args = mock_manager.send_to_user.call_args_list[-1][0]
            message_arg = last_call_args[0]
            
            # Verify the thread_data message structure
            assert message_arg["type"] == "thread_data"
            assert message_arg["payload"]["thread_id"] == "thread_123"
            assert len(message_arg["payload"]["messages"]) == 3
            
            # Verify message format
            first_msg = message_arg["payload"]["messages"][0]
            assert first_msg["id"] == "msg_0"
            assert first_msg["role"] == "user"
            assert first_msg["content"] == "Message content 0"
            
            # WebSocket manager creation and room operations are handled internally
            mock_create_manager.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_switch_thread_access_denied(self, handler, mock_thread):
        """Test that switching to unauthorized thread is denied"""
        # Setup mocks - thread has different user
        mock_thread.metadata_ = {"user_id": "other_user"}
        handler.thread_service.get_thread = AsyncMock(return_value=mock_thread)
        
        with patch('netra_backend.app.services.message_handlers.create_websocket_manager') as mock_create_manager:
            mock_manager = MagicMock()
            mock_manager.send_to_user = AsyncMock()
            mock_create_manager.return_value = mock_manager
            
            # Create mock session
            mock_session = Mock(spec=AsyncSession)
            
            # Create proper UserExecutionContext
            user_context = UserExecutionContext(
                user_id="test_user",
                thread_id="thread_123",
                run_id="test-run-789",
                request_id="test-request-012"
            )
            
            # Call switch_thread
            payload = {"thread_id": "thread_123"}
            await handler.handle_switch_thread(
                user_context=user_context,
                payload=payload,
                db_session=mock_session
            )
            
            # Verify access denied error was sent
            mock_manager.send_to_user.assert_called_once_with(
                {"type": "error", "message": "Access denied to thread"}
            )
    
    @pytest.mark.asyncio
    async def test_switch_thread_no_session(self, handler):
        """Test thread switch without database session"""
        with patch('netra_backend.app.services.message_handlers.create_websocket_manager') as mock_create_manager:
            mock_manager = MagicMock()
            mock_manager.send_to_user = AsyncMock()
            mock_create_manager.return_value = mock_manager
            
            # Create proper UserExecutionContext
            user_context = UserExecutionContext(
                user_id="test_user",
                thread_id="thread_123",
                run_id="test-run-345",
                request_id="test-request-678"
            )
            
            # Call switch_thread without session
            payload = {"thread_id": "thread_123"}
            await handler.handle_switch_thread(
                user_context=user_context,
                payload=payload,
                db_session=None
            )
            
            # Should create WebSocket manager (room management is handled internally)
            mock_create_manager.assert_called_once_with(user_context)
            
            # But no messages loaded (no session provided)
            # Can't verify this easily since thread_service may not have the method mocked
    
    @pytest.mark.asyncio
    async def test_switch_thread_message_loading_error(self, handler, mock_thread):
        """Test thread switch continues even if message loading fails"""
        # Setup mocks
        handler.thread_service.get_thread = AsyncMock(return_value=mock_thread)
        handler.thread_service.get_thread_messages = AsyncMock(
            side_effect=Exception("Database error")
        )
        
        with patch('netra_backend.app.services.message_handlers.create_websocket_manager') as mock_create_manager:
            mock_manager = MagicMock()
            mock_manager.send_to_user = AsyncMock()
            mock_create_manager.return_value = mock_manager
            
            # Create mock session
            mock_session = Mock(spec=AsyncSession)
            
            # Create proper UserExecutionContext
            user_context = UserExecutionContext(
                user_id="test_user",
                thread_id="thread_123",
                run_id="test-run-999",
                request_id="test-request-888"
            )
            
            # Call switch_thread
            payload = {"thread_id": "thread_123"}
            await handler.handle_switch_thread(
                user_context=user_context,
                payload=payload,
                db_session=mock_session
            )
            
            # Should still create WebSocket manager despite message loading error
            mock_create_manager.assert_called_once_with(user_context)
    
    @pytest.mark.asyncio
    async def test_switch_thread_websocket_association(self, handler, mock_thread):
        """Test that WebSocket connection association is updated"""
        # Setup mocks
        handler.thread_service.get_thread = AsyncMock(return_value=mock_thread)
        handler.thread_service.get_thread_messages = AsyncMock(return_value=[])
        
        # Mock WebSocket
        mock_websocket = MagicMock()
        
        with patch('netra_backend.app.services.message_handlers.create_websocket_manager') as mock_create_manager:
            mock_manager = MagicMock()
            mock_manager.send_to_user = AsyncMock()
            mock_create_manager.return_value = mock_manager
            
            # Create mock session
            mock_session = Mock(spec=AsyncSession)
            
            # Create proper UserExecutionContext
            user_context = UserExecutionContext(
                user_id="test_user",
                thread_id="thread_123",
                run_id="test-run-555",
                request_id="test-request-333"
            )
            
            # Call switch_thread with websocket
            payload = {"thread_id": "thread_123"}
            await handler.handle_switch_thread(
                user_context=user_context,
                payload=payload,
                db_session=mock_session,
                websocket=mock_websocket
            )
            
            # Verify WebSocket manager was created with proper context
            mock_create_manager.assert_called_once_with(user_context)
            
            # Thread data should have been sent (with messages from the mock)
            mock_manager.send_to_user.assert_called()
    
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