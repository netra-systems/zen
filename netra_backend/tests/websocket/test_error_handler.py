"""
Async tests for ErrorHandler - WebSocket message handler
Coverage Target: 85%
Business Value: Customer-facing functionality
"""

import pytest
import asyncio
import time
from unittest.mock import Mock, AsyncMock
from netra_backend.app.websocket_core.handlers import ErrorHandler
from netra_backend.app.websocket_core.types import WebSocketMessage, MessageType
from shared.isolated_environment import IsolatedEnvironment

@pytest.mark.asyncio
class ErrorHandlerAsyncTests:
    """Async test suite for ErrorHandler"""

    def setup_method(self):
        """Set up test environment"""
        self.handler = ErrorHandler()

    async def test_error_handler_initialization(self):
        """Test ErrorHandler initialization"""
        assert self.handler is not None
        assert hasattr(self.handler, 'error_stats')
        assert self.handler.error_stats["total_errors"] == 0
        assert MessageType.ERROR_MESSAGE in self.handler.supported_types

    async def test_handle_error_message(self):
        """Test error message handling"""
        # Create mock WebSocket
        mock_websocket = Mock()

        # Create error message
        error_message = WebSocketMessage(
            type=MessageType.ERROR_MESSAGE,
            payload={
                "error_code": "TEST_ERROR",
                "error_message": "Test error message"
            }
        )

        # Handle the message
        result = await self.handler.handle_message("test_user", mock_websocket, error_message)

        # Verify handling
        assert result is not None  # Should handle the message
        assert self.handler.error_stats["total_errors"] == 1
        assert self.handler.error_stats["last_error_time"] is not None

    async def test_error_stats_tracking(self):
        """Test error statistics tracking"""
        mock_websocket = Mock()

        # Handle multiple error messages
        for i in range(3):
            error_message = WebSocketMessage(
                type=MessageType.ERROR_MESSAGE,
                payload={
                    "error_code": f"ERROR_{i}",
                    "error_message": f"Test error {i}"
                }
            )
            await self.handler.handle_message(f"user_{i}", mock_websocket, error_message)

        # Check stats
        assert self.handler.error_stats["total_errors"] == 3
        assert self.handler.error_stats["last_error_time"] is not None

    async def test_error_handler_base_functionality(self):
        """Test base handler functionality"""
        # Test that handler accepts correct message types
        assert MessageType.ERROR_MESSAGE in self.handler.supported_types

        # Test that handler rejects other message types
        assert MessageType.USER_MESSAGE not in self.handler.supported_types
