"""
Test to reproduce and verify fix for async context manager misuse bug.

This test reproduces the critical bug where chat dies after triage agent
due to incorrect usage of async context manager as async generator.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager

from netra_backend.app.websocket_core.agent_handler import AgentMessageHandler
from netra_backend.app.websocket_core.types import MessageType, WebSocketMessage


class TestAsyncContextManagerFix:
    """Test the critical async context manager fix."""

    @pytest.mark.asyncio
    async def test_reproduce_async_for_error(self):
        """Reproduce the exact error: 'async for' requires an object with __aiter__ method."""
        
        # Create an async context manager (like the one in dependencies.py)
        @asynccontextmanager
        async def mock_get_request_scoped_db_session():
            """Mock that returns an async context manager."""
            mock_session = AsyncMock()
            try:
                yield mock_session
            finally:
                await mock_session.close()
        
        # This should fail with the exact error we see in production
        with pytest.raises(TypeError) as exc_info:
            async for session in mock_get_request_scoped_db_session():
                pass
        
        assert "'async for' requires an object with __aiter__ method" in str(exc_info.value)
        assert "_AsyncGeneratorContextManager" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_correct_async_with_usage(self):
        """Test the correct usage with async with."""
        
        # Create an async context manager
        @asynccontextmanager
        async def mock_get_request_scoped_db_session():
            """Mock that returns an async context manager."""
            mock_session = AsyncMock()
            try:
                yield mock_session
            finally:
                await mock_session.close()
        
        # This should work correctly
        async with mock_get_request_scoped_db_session() as session:
            assert session is not None
            # Session should be usable
            await session.execute(AsyncMock())

    @pytest.mark.asyncio
    async def test_agent_handler_with_fixed_pattern(self):
        """Test that AgentMessageHandler works with the fixed pattern."""
        
        handler = AgentMessageHandler()
        
        # Mock dependencies
        mock_websocket = AsyncMock()
        mock_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"agent_name": "triage", "user_request": "test"}
        )
        
        # Mock the database session getter with correct pattern
        mock_session = AsyncMock()
        
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_getter:
            # Make it an async context manager
            @asynccontextmanager
            async def mock_context_manager():
                yield mock_session
            
            mock_getter.return_value = mock_context_manager()
            
            # Mock the message handler service
            with patch('netra_backend.app.websocket_core.agent_handler.MessageHandlerService') as mock_service_class:
                mock_service = AsyncMock()
                mock_service.handle_start_agent.return_value = {
                    "success": True,
                    "run_id": "test_run_123",
                    "agent": "triage"
                }
                mock_service_class.return_value = mock_service
                
                # This should work without the async for error
                result = await handler.handle_message(
                    user_id="test_user",
                    message=mock_message,
                    websocket=mock_websocket
                )
                
                # Should have called the service
                mock_service.handle_start_agent.assert_called_once()

    @pytest.mark.asyncio 
    async def test_verify_current_broken_pattern(self):
        """Verify the current broken pattern in agent_handler.py."""
        
        handler = AgentMessageHandler()
        
        mock_websocket = AsyncMock()
        mock_message = WebSocketMessage(
            type=MessageType.START_AGENT,
            payload={"agent_name": "triage", "user_request": "test"}
        )
        
        # Mock with the actual async context manager from dependencies.py
        with patch('netra_backend.app.websocket_core.agent_handler.get_request_scoped_db_session') as mock_getter:
            @asynccontextmanager
            async def mock_context_manager():
                yield AsyncMock()
            
            # Return the context manager itself (not called)
            mock_getter.return_value = mock_context_manager()
            
            # This should fail with the exact production error
            with pytest.raises(TypeError) as exc_info:
                await handler.handle_message(
                    user_id="test_user",
                    message=mock_message,
                    websocket=mock_websocket
                )
            
            error_msg = str(exc_info.value)
            assert ("'async for' requires an object with __aiter__ method" in error_msg or
                    "_AsyncGeneratorContextManager" in error_msg)