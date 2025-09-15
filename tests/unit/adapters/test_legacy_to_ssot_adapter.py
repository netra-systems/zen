"""
Test Suite for LegacyToSSOTAdapter - Issue #1099

This test suite validates the adapter functionality that bridges legacy
and SSOT message handler interfaces during the migration period.

Test Coverage:
1. Parameter conversion (Dict payload -> WebSocketMessage)
2. Return type normalization (None -> bool)
3. Error handling (Exception -> return code)
4. Message type mapping (string -> MessageType enum)
5. Backward compatibility validation
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from typing import Dict, Any

from netra_backend.app.adapters.legacy_to_ssot_adapter import (
    LegacyToSSOTAdapter,
    ParameterConverter,
    ReturnTypeNormalizer,
    create_legacy_adapter
)
from netra_backend.app.websocket_core.types import (
    WebSocketMessage,
    MessageType,
    create_standard_message
)
from fastapi import WebSocket


class MockLegacyHandler:
    """Mock legacy handler for testing."""
    
    def __init__(self, message_type: str = "start_agent"):
        self.message_type = message_type
        self.handle_calls = []
        self.should_raise = False
    
    def get_message_type(self) -> str:
        return self.message_type
    
    async def handle(self, user_id: str, payload: Dict[str, Any]) -> None:
        self.handle_calls.append((user_id, payload))
        if self.should_raise:
            raise RuntimeError("Mock legacy handler error")


class TestParameterConverter:
    """Test parameter conversion utilities."""
    
    def test_payload_to_websocket_message_basic(self):
        """Test basic payload to WebSocketMessage conversion."""
        payload = {
            "type": "start_agent",
            "user_request": "Create analysis",
            "thread_id": "thread_123",
            "run_id": "run_456"
        }
        
        message = ParameterConverter.payload_to_websocket_message(payload)
        
        assert message.type == MessageType.START_AGENT
        assert message.thread_id == "thread_123"
        assert message.payload["run_id"] == "run_456"  # run_id is in payload, not message field
        assert message.payload["user_request"] == "Create analysis"
        assert "type" not in message.payload  # Should be removed from payload
        assert "thread_id" not in message.payload  # Should be removed from payload
    
    def test_payload_to_websocket_message_unknown_type(self):
        """Test conversion with unknown message type."""
        payload = {
            "type": "unknown_message_type",
            "data": "test"
        }
        
        message = ParameterConverter.payload_to_websocket_message(payload)
        
        # Should default to USER_MESSAGE for unknown types
        assert message.type == MessageType.USER_MESSAGE
        assert message.payload["data"] == "test"
    
    def test_payload_to_websocket_message_no_type(self):
        """Test conversion when type field is missing."""
        payload = {
            "user_request": "test without type"
        }
        
        message = ParameterConverter.payload_to_websocket_message(payload)
        
        # Should default to USER_MESSAGE when type is missing
        assert message.type == MessageType.USER_MESSAGE
        assert message.payload["user_request"] == "test without type"
    
    def test_create_mock_websocket(self):
        """Test mock WebSocket creation."""
        mock_websocket = ParameterConverter.create_mock_websocket()
        
        assert isinstance(mock_websocket, Mock)
        # Should be mocked as WebSocket spec  
        assert str(mock_websocket).startswith('<Mock spec=\'WebSocket\'')


class TestReturnTypeNormalizer:
    """Test return type normalization utilities."""
    
    def test_none_to_bool_success(self):
        """Test converting None to bool for successful operation."""
        result = ReturnTypeNormalizer.none_to_bool(None, exception_occurred=False)
        assert result is True
    
    def test_none_to_bool_failure(self):
        """Test converting None to bool when exception occurred."""
        result = ReturnTypeNormalizer.none_to_bool(None, exception_occurred=True)
        assert result is False
    
    def test_bool_to_none_success(self):
        """Test converting True to None (success)."""
        result = ReturnTypeNormalizer.bool_to_none(True)
        assert result is None
    
    def test_bool_to_none_failure(self):
        """Test converting False to exception (failure)."""
        with pytest.raises(RuntimeError, match="Handler returned failure"):
            ReturnTypeNormalizer.bool_to_none(False)


class TestLegacyToSSOTAdapter:
    """Test the main adapter functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_legacy_handler = MockLegacyHandler()
        self.adapter = LegacyToSSOTAdapter(self.mock_legacy_handler)
        self.mock_websocket = Mock(spec=WebSocket)
    
    def test_adapter_initialization(self):
        """Test adapter initialization."""
        assert self.adapter.legacy_handler == self.mock_legacy_handler
        assert hasattr(self.adapter, 'parameter_converter')
        assert hasattr(self.adapter, 'return_normalizer')
    
    def test_can_handle_matching_type(self):
        """Test can_handle with matching message type."""
        self.mock_legacy_handler.message_type = "start_agent"
        
        result = self.adapter.can_handle(MessageType.START_AGENT)
        assert result is True
    
    def test_can_handle_non_matching_type(self):
        """Test can_handle with non-matching message type."""
        self.mock_legacy_handler.message_type = "start_agent"
        
        result = self.adapter.can_handle(MessageType.USER_MESSAGE)
        assert result is False
    
    def test_can_handle_handler_without_type_method(self):
        """Test can_handle with handler that doesn't implement get_message_type."""
        handler_without_type = Mock()
        # Remove get_message_type method
        del handler_without_type.get_message_type
        
        adapter = LegacyToSSOTAdapter(handler_without_type)
        
        # Should return True as fallback for handlers without type specification
        result = adapter.can_handle(MessageType.START_AGENT)
        assert result is True
    
    @pytest.mark.asyncio
    async def test_handle_message_success(self):
        """Test successful message handling through adapter."""
        message = create_standard_message(
            MessageType.START_AGENT,
            {"user_request": "Create analysis", "run_id": "run_456"},
            thread_id="thread_123"
        )
        
        result = await self.adapter.handle_message("user_123", self.mock_websocket, message)
        
        # Should return True for successful handling
        assert result is True
        
        # Verify legacy handler was called correctly
        assert len(self.mock_legacy_handler.handle_calls) == 1
        user_id, payload = self.mock_legacy_handler.handle_calls[0]
        
        assert user_id == "user_123"
        assert payload["type"] == "start_agent"
        assert payload["user_request"] == "Create analysis"
        assert payload["thread_id"] == "thread_123"
        assert payload["run_id"] == "run_456"
    
    @pytest.mark.asyncio
    async def test_handle_message_legacy_exception(self):
        """Test handling when legacy handler raises exception."""
        self.mock_legacy_handler.should_raise = True
        
        message = create_standard_message(
            MessageType.START_AGENT,
            {"user_request": "test"}
        )
        
        result = await self.adapter.handle_message("user_123", self.mock_websocket, message)
        
        # Should return False when legacy handler raises exception
        assert result is False
    
    @pytest.mark.asyncio
    async def test_handle_message_adapter_exception(self):
        """Test handling when adapter itself encounters error."""
        # Test with valid message but make legacy handler fail unpredictably
        message = create_standard_message(MessageType.START_AGENT, {"test": "data"})
        
        # Override the adapter's convert method to force an error
        original_convert = self.adapter._convert_message_to_payload
        def failing_convert(msg):
            raise RuntimeError("Adapter conversion error")
        self.adapter._convert_message_to_payload = failing_convert
        
        result = await self.adapter.handle_message("user_123", self.mock_websocket, message)
        
        # Should return False when adapter encounters error
        assert result is False
        
        # Restore original method
        self.adapter._convert_message_to_payload = original_convert
    
    def test_get_legacy_handler(self):
        """Test getting wrapped legacy handler."""
        handler = self.adapter.get_legacy_handler()
        assert handler == self.mock_legacy_handler
    
    def test_get_message_type(self):
        """Test getting message type from wrapped handler."""
        self.mock_legacy_handler.message_type = "custom_type"
        
        message_type = self.adapter.get_message_type()
        assert message_type == "custom_type"
    
    def test_get_message_type_handler_without_method(self):
        """Test getting message type when handler doesn't have the method."""
        handler_without_type = Mock()
        del handler_without_type.get_message_type
        
        adapter = LegacyToSSOTAdapter(handler_without_type)
        message_type = adapter.get_message_type()
        
        assert message_type == "unknown"
    
    def test_convert_message_to_payload(self):
        """Test internal message to payload conversion."""
        message = create_standard_message(
            MessageType.USER_MESSAGE,
            {"content": "test content", "run_id": "run_456"},
            thread_id="thread_123"
        )
        
        payload = self.adapter._convert_message_to_payload(message)
        
        assert payload["type"] == "user_message"
        assert payload["content"] == "test content"
        assert payload["thread_id"] == "thread_123"
        assert payload["run_id"] == "run_456"
    
    def test_convert_message_to_payload_empty_message(self):
        """Test conversion with empty message payload."""
        message = create_standard_message(MessageType.CHAT, None)
        
        payload = self.adapter._convert_message_to_payload(message)
        
        assert payload["type"] == "chat"
        # Should handle None payload gracefully


class TestAdapterIntegration:
    """Integration tests for adapter functionality."""
    
    @pytest.mark.asyncio
    async def test_multiple_handlers_concurrent(self):
        """Test multiple adapted handlers working concurrently."""
        # Create multiple handlers
        handler1 = MockLegacyHandler("start_agent")
        handler2 = MockLegacyHandler("user_message")
        handler3 = MockLegacyHandler("chat")
        
        adapter1 = LegacyToSSOTAdapter(handler1)
        adapter2 = LegacyToSSOTAdapter(handler2)
        adapter3 = LegacyToSSOTAdapter(handler3)
        
        # Create messages for each handler
        message1 = create_standard_message(MessageType.START_AGENT, {"data": "test1"})
        message2 = create_standard_message(MessageType.USER_MESSAGE, {"data": "test2"})
        message3 = create_standard_message(MessageType.CHAT, {"data": "test3"})
        
        websocket = Mock(spec=WebSocket)
        
        # Process concurrently
        results = await asyncio.gather(
            adapter1.handle_message("user1", websocket, message1),
            adapter2.handle_message("user2", websocket, message2),
            adapter3.handle_message("user3", websocket, message3)
        )
        
        # All should succeed
        assert all(results)
        
        # Verify each handler was called correctly
        assert len(handler1.handle_calls) == 1
        assert len(handler2.handle_calls) == 1
        assert len(handler3.handle_calls) == 1
        
        assert handler1.handle_calls[0][0] == "user1"
        assert handler2.handle_calls[0][0] == "user2"
        assert handler3.handle_calls[0][0] == "user3"


class TestBackwardCompatibility:
    """Test backward compatibility functions."""
    
    def test_create_legacy_adapter_function(self):
        """Test the create_legacy_adapter helper function."""
        mock_handler = MockLegacyHandler()
        
        adapter = create_legacy_adapter(mock_handler)
        
        assert isinstance(adapter, LegacyToSSOTAdapter)
        assert adapter.legacy_handler == mock_handler


class TestAdapterErrorHandling:
    """Test error handling and edge cases."""
    
    @pytest.mark.asyncio
    async def test_adapter_with_async_exception_in_legacy_handler(self):
        """Test adapter handling of async exceptions in legacy handler."""
        mock_handler = MockLegacyHandler()
        
        async def failing_handle(user_id, payload):
            await asyncio.sleep(0.01)  # Simulate async work
            raise ValueError("Async failure")
        
        mock_handler.handle = failing_handle
        adapter = LegacyToSSOTAdapter(mock_handler)
        
        message = create_standard_message(MessageType.START_AGENT, {"test": "data"})
        websocket = Mock(spec=WebSocket)
        
        result = await adapter.handle_message("user_123", websocket, message)
        
        # Should handle async exceptions and return False
        assert result is False
    
    def test_adapter_with_malformed_legacy_handler(self):
        """Test adapter with handler that doesn't follow expected interface."""
        malformed_handler = Mock()
        # Handler without required methods
        del malformed_handler.get_message_type
        
        adapter = LegacyToSSOTAdapter(malformed_handler)
        
        # Should handle gracefully
        assert adapter.get_message_type() == "unknown"
        assert adapter.can_handle(MessageType.START_AGENT) is True


if __name__ == "__main__":
    # Run adapter tests
    print("🔍 Running LegacyToSSOTAdapter Tests for Issue #1099")
    print("=" * 60)
    
    exit_code = pytest.main([
        __file__, 
        "-v", 
        "--tb=short"
    ])
    
    if exit_code == 0:
        print("\n✅ ALL ADAPTER TESTS PASSED")
        print("LegacyToSSOTAdapter is ready for production use")
    else:
        print(f"\n❌ ADAPTER TESTS FAILED (exit code: {exit_code})")
        print("Adapter needs fixes before migration can continue")
    
    exit(exit_code)