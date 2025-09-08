import sys
from pathlib import Path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

import asyncio
import json
from unittest.mock import MagicMock, AsyncMock, Mock, patch

import pytest
from fastapi import WebSocket
from netra_backend.app.routes.utils.websocket_helpers import (
    handle_pong_message,
    parse_json_message,
    receive_message_with_timeout,
    validate_and_handle_message,
)

class TestWebSocketAdvanced:
    
    @pytest.mark.asyncio
    async def test_parse_json_message_valid(self):
        """Test parsing valid JSON message"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_manager.send_message = AsyncMock()  # TODO: Use real service instance
        
        # Test valid JSON
        result = await parse_json_message('{"type": "test", "content": "hello"}', "user-123", mock_manager)
        
        assert result == {"type": "test", "content": "hello"}
        mock_manager.send_message.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_parse_json_message_invalid(self):
        """Test parsing invalid JSON message"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_manager.send_message = AsyncMock()  # TODO: Use real service instance
        
        # Test invalid JSON
        result = await parse_json_message('invalid json', "user-123", mock_manager)
        
        assert result is None
        mock_manager.send_message.assert_called_once()
        # Verify error message was sent
        call_args = mock_manager.send_message.call_args
        assert call_args[0][0] == "user-123"
        assert call_args[0][1]["type"] == "error"
        assert "PARSING_ERROR" in call_args[0][1]["code"]
    
    @pytest.mark.asyncio
    async def test_parse_json_message_none(self):
        """Test parsing None message"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_manager.send_message = AsyncMock()  # TODO: Use real service instance
        
        # Test None input
        result = await parse_json_message(None, "user-123", mock_manager)
        
        assert result is None
        mock_manager.send_message.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_pong_message_raw_pong(self):
        """Test handling raw pong message"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_manager.handle_pong = AsyncMock()  # TODO: Use real service instance
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        
        # Test raw pong
        result = await handle_pong_message("pong", "user-123", mock_websocket, mock_manager)
        
        assert result is True
        mock_manager.handle_pong.assert_called_once_with("user-123", mock_websocket)
    
    @pytest.mark.asyncio
    async def test_handle_pong_message_json_ping(self):
        """Test handling JSON ping message"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.send_json = AsyncMock()  # TODO: Use real service instance
        
        # Test JSON ping
        ping_message = '{"type": "ping", "timestamp": 123456}'
        result = await handle_pong_message(ping_message, "user-123", mock_websocket, mock_manager)
        
        assert result is True
        mock_websocket.send_json.assert_called_once()
        # Verify pong response was sent
        call_args = mock_websocket.send_json.call_args[0][0]
        assert call_args["type"] == "pong"
    
    @pytest.mark.asyncio
    async def test_handle_pong_message_not_pong(self):
        """Test handling non-pong message"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        
        # Test regular message
        result = await handle_pong_message('{"type": "message", "content": "hello"}', "user-123", mock_websocket, mock_manager)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_and_handle_message_ping(self):
        """Test validate and handle ping message"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.send_json = AsyncMock()  # TODO: Use real service instance
        
        ping_message = {"type": "ping", "timestamp": 123456}
        
        # Test ping message handling
        result = await validate_and_handle_message("user-123", mock_websocket, ping_message, mock_manager)
        
        assert result is True
        mock_websocket.send_json.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_validate_and_handle_message_invalid_structure(self):
        """Test validate and handle message with invalid structure"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_manager.send_message = AsyncMock()  # TODO: Use real service instance
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        
        # Test None message
        result = await validate_and_handle_message("user-123", mock_websocket, None, mock_manager)
        
        assert result is True  # Connection kept alive
        mock_manager.send_message.assert_called_once()
        
        # Verify error message
        call_args = mock_manager.send_message.call_args
        assert call_args[0][0] == "user-123"
        assert call_args[0][1]["type"] == "error"
        assert call_args[0][1]["code"] == "EMPTY_MESSAGE"
    
    @pytest.mark.asyncio 
    async def test_validate_and_handle_message_missing_type(self):
        """Test validate and handle message missing type field"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        mock_manager.send_message = AsyncMock()  # TODO: Use real service instance
        mock_websocket = MagicMock(spec=WebSocket)
        
        # Test message without type
        message = {"content": "hello", "user": "test"}
        result = await validate_and_handle_message("user-123", mock_websocket, message, mock_manager)
        
        assert result is True  # Connection kept alive
        mock_manager.send_message.assert_called_once()
        
        # Verify error message
        call_args = mock_manager.send_message.call_args
        assert call_args[0][0] == "user-123" 
        assert call_args[0][1]["type"] == "error"
        assert call_args[0][1]["code"] == "MISSING_TYPE_FIELD"
    
    @pytest.mark.asyncio
    async def test_validate_and_handle_message_valid_message(self):
        """Test validate and handle valid message"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        # Mock: Async component isolation for testing without real async operations
        mock_manager.handle_message = AsyncMock(return_value=True)
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        
        # Test valid message
        message = {"type": "user_message", "content": "Hello", "thread_id": "123"}
        result = await validate_and_handle_message("user-123", mock_websocket, message, mock_manager)
        
        assert result is True
        mock_manager.handle_message.assert_called_once_with("user-123", mock_websocket, message)
    
    @pytest.mark.asyncio
    async def test_receive_message_with_timeout_success(self):
        """Test receiving message with timeout - success case"""
        
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket.receive_text = AsyncMock(return_value='{"type": "test"}')
        
        # Test successful message receive
        result = await receive_message_with_timeout(mock_websocket)
        
        assert result == '{"type": "test"}'
        mock_websocket.receive_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_receive_message_with_timeout_timeout(self):
        """Test receiving message with timeout - timeout case"""
        
        # Mock: WebSocket infrastructure isolation for unit tests without real connections
        mock_websocket = MagicMock(spec=WebSocket)
        
        # Mock a slow receive_text that will timeout
        async def slow_receive():
            await asyncio.sleep(35)  # Longer than timeout
            return "delayed message"
        
        mock_websocket.receive_text = slow_receive
        
        # Test timeout
        with pytest.raises(asyncio.TimeoutError):
            await receive_message_with_timeout(mock_websocket)
    
    @pytest.mark.asyncio
    async def test_parse_json_message_empty_string(self):
        """Test parsing empty string message"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_manager.send_message = AsyncMock()  # TODO: Use real service instance
        
        # Test empty string
        result = await parse_json_message("", "user-123", mock_manager)
        
        assert result is None
        mock_manager.send_message.assert_called_once()
        
        # Verify error message
        call_args = mock_manager.send_message.call_args
        assert call_args[0][1]["code"] == "PARSING_ERROR"
    
    @pytest.mark.asyncio
    async def test_parse_json_message_non_object(self):
        """Test parsing JSON that's not an object"""
        
        # Mock: Generic component isolation for controlled unit testing
        mock_manager = MagicMock()  # TODO: Use real service instance
        # Mock: Generic component isolation for controlled unit testing
        mock_manager.send_message = AsyncMock()  # TODO: Use real service instance
        
        # Test JSON array instead of object
        result = await parse_json_message('["not", "an", "object"]', "user-123", mock_manager)
        
        assert result is None
        mock_manager.send_message.assert_called_once()
        
        # Verify error message
        call_args = mock_manager.send_message.call_args
        assert call_args[0][1]["code"] == "PARSING_ERROR"
        assert "JSON object" in call_args[0][1]["error"]