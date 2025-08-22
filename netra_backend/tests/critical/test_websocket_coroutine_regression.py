"""Critical test suite to prevent WebSocket coroutine regression.

Business Value: Prevents WebSocket failures that disconnect users, protecting $8K MRR.
Tests ensure proper async/await usage and coroutine handling in WebSocket message processing.
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from fastapi import WebSocket
from netra_backend.app.routes.utils.websocket_helpers import (
    _handle_ping_message,
    _handle_with_manager,
    parse_json_message,
    validate_and_handle_message,
)

class TestCoroutineHandling:
    """Test proper coroutine handling in WebSocket message processing."""
    
    @pytest.mark.asyncio
    async def test_parse_json_message_rejects_coroutine(self):
        """Verify parse_json_message detects and rejects coroutine objects."""
        async def fake_coroutine():
            return {"type": "test"}
        
        manager = Mock()
        manager.send_error = AsyncMock()
        
        # Pass coroutine object (not awaited)
        coroutine_obj = fake_coroutine()
        result = await parse_json_message(coroutine_obj, "test_user", manager)
        
        assert result is None
        manager.send_error.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_parse_json_message_handles_valid_json(self):
        """Verify parse_json_message properly handles valid JSON string."""
        manager = Mock()
        manager.send_error = AsyncMock()
        
        valid_json = '{"type": "ping", "data": "test"}'
        result = await parse_json_message(valid_json, "test_user", manager)
        
        assert result == {"type": "ping", "data": "test"}
        manager.send_error.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_parse_json_message_handles_dict_passthrough(self):
        """Verify parse_json_message passes through dict objects."""
        manager = Mock()
        manager.send_error = AsyncMock()
        
        dict_data = {"type": "ping", "data": "test"}
        result = await parse_json_message(dict_data, "test_user", manager)
        
        assert result == dict_data
        manager.send_error.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_parse_json_message_handles_invalid_json(self):
        """Verify parse_json_message handles invalid JSON gracefully."""
        manager = Mock()
        manager.send_error = AsyncMock()
        
        invalid_json = '{"type": "ping", invalid}'
        result = await parse_json_message(invalid_json, "test_user", manager)
        
        assert result is None
        manager.send_error.assert_called_once_with(
            "test_user", "Invalid JSON message format"
        )
    
    @pytest.mark.asyncio
    async def test_handle_ping_message_rejects_coroutine(self):
        """Verify _handle_ping_message detects and rejects coroutine objects."""
        async def fake_message():
            return {"type": "ping"}
        
        websocket = Mock(spec=WebSocket)
        
        # Pass coroutine object (not awaited)
        coroutine_obj = fake_message()
        result = await _handle_ping_message(coroutine_obj, websocket)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_handle_ping_message_processes_ping(self):
        """Verify _handle_ping_message properly handles ping messages."""
        websocket = Mock(spec=WebSocket)
        websocket.send_json = AsyncMock()
        
        ping_message = {"type": "ping"}
        with patch('app.routes.utils.websocket_helpers._send_pong_response', new=AsyncMock()):
            result = await _handle_ping_message(ping_message, websocket)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_handle_ping_message_ignores_non_ping(self):
        """Verify _handle_ping_message ignores non-ping messages."""
        websocket = Mock(spec=WebSocket)
        
        non_ping_message = {"type": "message", "content": "test"}
        result = await _handle_ping_message(non_ping_message, websocket)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_validate_and_handle_message_with_ping(self):
        """Verify validate_and_handle_message processes ping correctly."""
        websocket = Mock(spec=WebSocket)
        manager = Mock()
        
        ping_message = {"type": "ping"}
        with patch('app.routes.utils.websocket_helpers._handle_ping_message', 
                  new=AsyncMock(return_value=True)):
            result = await validate_and_handle_message(
                "test_user", websocket, ping_message, manager
            )
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_validate_and_handle_message_delegates_to_manager(self):
        """Verify validate_and_handle_message delegates non-ping to manager."""
        websocket = Mock(spec=WebSocket)
        manager = Mock()
        manager.handle_message = AsyncMock(return_value=True)
        
        regular_message = {"type": "message", "content": "test"}
        with patch('app.routes.utils.websocket_helpers._handle_ping_message',
                  new=AsyncMock(return_value=False)):
            result = await validate_and_handle_message(
                "test_user", websocket, regular_message, manager
            )
        
        assert result is True
        manager.handle_message.assert_called_once_with(
            "test_user", websocket, regular_message
        )
    
    @pytest.mark.asyncio
    async def test_handle_with_manager_returns_false_on_failure(self):
        """Verify _handle_with_manager returns False when manager fails."""
        websocket = Mock(spec=WebSocket)
        manager = Mock()
        manager.handle_message = AsyncMock(return_value=False)
        
        message = {"type": "message"}
        result = await _handle_with_manager("test_user", websocket, message, manager)
        
        assert result is False

class TestAsyncAwaitChain:
    """Test proper async/await chain in message processing."""
    
    @pytest.mark.asyncio
    async def test_full_message_processing_chain(self):
        """Verify entire message processing chain awaits properly."""
        from netra_backend.app.routes.websocket_secure import _process_single_message
        
        websocket = Mock(spec=WebSocket)
        websocket.receive_text = AsyncMock(return_value='{"type": "test"}')
        
        agent_service = Mock()
        agent_service.handle_websocket_message = AsyncMock()
        
        manager = Mock()
        manager.handle_message = AsyncMock(return_value=True)
        manager.send_error = AsyncMock()
        
        with patch('app.routes.websockets.manager', manager), \
             patch('app.routes.websockets.receive_message_with_timeout',
                   new=AsyncMock(return_value='{"type": "test"}')), \
             patch('app.routes.websockets.handle_pong_message',
                   new=AsyncMock(return_value=False)), \
             patch('app.routes.websockets.process_agent_message',
                   new=AsyncMock()):
            
            # Should not raise any coroutine-related errors
            await _process_single_message("test_user", websocket, agent_service)
    
    @pytest.mark.asyncio
    async def test_coroutine_detection_in_pipeline(self):
        """Test that coroutines are detected early in the pipeline."""
        async def fake_receive():
            return '{"type": "test"}'
        
        websocket = Mock(spec=WebSocket)
        agent_service = Mock()
        manager = Mock()
        
        with patch('app.routes.websockets.manager', manager), \
             patch('app.routes.websockets.receive_message_with_timeout',
                   return_value=fake_receive()):  # Returns coroutine, not awaited
            
            # The parse_json_message should handle the coroutine gracefully
            with patch('app.routes.websockets.parse_json_message',
                      new=AsyncMock(return_value=None)) as mock_parse:
                await _process_single_message("test_user", websocket, agent_service)
                
                # Verify parse_json_message was called
                mock_parse.assert_called_once()

class TestCoroutineErrorScenarios:
    """Test various error scenarios with coroutines."""
    
    @pytest.mark.asyncio
    async def test_nested_coroutine_handling(self):
        """Test handling of nested coroutines in message data."""
        async def inner_coroutine():
            return "data"
        
        async def outer_coroutine():
            return inner_coroutine()  # Returns coroutine, not awaited
        
        manager = Mock()
        manager.send_error = AsyncMock()
        
        # Get the nested coroutine
        nested = await outer_coroutine()
        
        # Should detect it's a coroutine
        result = await parse_json_message(nested, "test_user", manager)
        assert result is None
    
    @pytest.mark.asyncio
    async def test_mixed_valid_and_coroutine_messages(self):
        """Test handling mix of valid messages and coroutines."""
        manager = Mock()
        manager.send_error = AsyncMock()
        manager.handle_message = AsyncMock(return_value=True)
        websocket = Mock(spec=WebSocket)
        
        # Valid message
        valid_msg = {"type": "message", "content": "test"}
        result1 = await validate_and_handle_message(
            "user1", websocket, valid_msg, manager
        )
        assert result1 is True
        
        # Coroutine (should be handled gracefully)
        async def fake_msg():
            return {"type": "message"}
        
        with patch('app.routes.utils.websocket_helpers._handle_ping_message',
                  new=AsyncMock(return_value=False)):
            coroutine_msg = fake_msg()
            # Should handle without crashing
            result2 = await validate_and_handle_message(
                "user2", websocket, coroutine_msg, manager
            )
    
    @pytest.mark.asyncio
    async def test_exception_handling_with_coroutines(self):
        """Test exception handling when coroutines are involved."""
        manager = Mock()
        manager.send_error = AsyncMock(side_effect=Exception("Send error failed"))
        
        # Invalid JSON that will trigger send_error
        invalid_json = '{"invalid": json}'
        
        # Should handle exception gracefully
        result = await parse_json_message(invalid_json, "test_user", manager)
        assert result is None

class TestRegressionPrevention:
    """Specific tests to prevent regression of the coroutine error."""
    
    @pytest.mark.asyncio
    async def test_message_get_attribute_access(self):
        """Ensure message.get() is never called on coroutines."""
        websocket = Mock(spec=WebSocket)
        
        # Test with valid dict
        valid_message = {"type": "ping", "data": "test"}
        can_access = hasattr(valid_message, 'get')
        assert can_access is True
        assert valid_message.get("type") == "ping"
        
        # Test with coroutine
        async def coroutine_message():
            return {"type": "ping"}
        
        coro = coroutine_message()
        can_access_coro = hasattr(coro, 'get')
        assert can_access_coro is False
        
        # Verify our handler rejects it
        result = await _handle_ping_message(coro, websocket)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_all_await_points_present(self):
        """Verify all async functions are properly awaited."""
        # This test checks that common async functions are awaited
        import inspect

        from netra_backend.app.routes import websockets
        
        # Get the source of _process_single_message
        source = inspect.getsource(websockets._process_single_message)
        
        # Check for proper await usage
        assert "await receive_message_with_timeout" in source
        assert "await parse_json_message" in source
        assert "await handle_pong_message" in source
        assert "await _handle_parsed_message" in source
    
    @pytest.mark.asyncio 
    async def test_coroutine_early_detection(self):
        """Test that coroutines are detected as early as possible."""
        import time
        start = time.time()
        
        async def slow_coroutine():
            await asyncio.sleep(1)
            return {"type": "test"}
        
        manager = Mock()
        manager.send_error = AsyncMock()
        
        # Should detect coroutine immediately without awaiting it
        coro = slow_coroutine()
        result = await parse_json_message(coro, "test_user", manager)
        
        elapsed = time.time() - start
        assert elapsed < 0.1  # Should return immediately, not wait for sleep
        assert result is None