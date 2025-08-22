"""WebSocket Message Type Safety Tests - Main Entry Point.

Entry point for WebSocket message type safety testing suite.
Imports and orchestrates tests from focused modules.
"""

import sys
from pathlib import Path

from test_framework import setup_test_path

import pytest

from netra_backend.tests.test_websocket_bidirectional_types import (
    TestBidirectionalTypeConsistency,
    TestWebSocketMessageValidation,
    TestWebSocketSendToThread,
)
from netra_backend.tests.test_websocket_client_to_server_types import (
    TestClientMessageBatchValidation,
    TestClientToServerMessageTypes,
)
from netra_backend.tests.test_websocket_server_to_client_types import (
    TestServerMessageBatchValidation,
    TestServerToClientMessageTypes,
)

# Import from the focused modules
from netra_backend.tests.test_websocket_type_safety_factory import (
    WebSocketMessageFactory,
    WebSocketTestDataFactory,
)

class TestWebSocketTypeSafetyMain:
    """Main test class that orchestrates all WebSocket type safety tests."""
    
    def test_complete_type_safety_suite(self):
        """Run the complete type safety testing suite."""
        print("Running complete WebSocket type safety testing suite...")
        
        # Test client-to-server messages
        client_tests = TestClientToServerMessageTypes()
        client_tests.test_start_agent_message_validation()
        client_tests.test_user_message_validation()
        client_tests.test_thread_operations_validation()
        client_tests.test_control_messages_validation()
        
        # Test server-to-client messages
        server_tests = TestServerToClientMessageTypes()
        server_tests.test_agent_lifecycle_messages_validation()
        server_tests.test_tool_messages_validation()
        server_tests.test_streaming_messages_validation()
        server_tests.test_error_message_validation()
        
        # Test bidirectional consistency
        bidirectional_tests = TestBidirectionalTypeConsistency()
        bidirectional_tests.test_request_response_pairing()
        bidirectional_tests.test_message_id_tracking()
        bidirectional_tests.test_connection_state_transitions()
        
        print("Complete type safety testing suite completed successfully!")
    
    def test_message_factory_functionality(self):
        """Test message factory functionality."""
        print("Testing message factory functionality...")
        
        # Test client message creation
        client_msg = WebSocketMessageFactory.create_client_message(
            "start_agent",
            {"query": "Test", "user_id": "user123"}
        )
        assert client_msg["type"] == "start_agent"
        assert "message_id" in client_msg
        
        # Test server message creation
        server_msg = WebSocketMessageFactory.create_server_message(
            "agent_started",
            {"run_id": "run123"}
        )
        assert server_msg["type"] == "agent_started"
        assert "message_id" in server_msg
        
        print("Message factory functionality tests passed!")
    
    def test_validation_error_handling(self):
        """Test validation error handling."""
        print("Testing validation error handling...")
        
        validation_tests = TestWebSocketMessageValidation()
        validation_tests.test_invalid_message_type_handling()
        validation_tests.test_enum_validation_comprehensive()
        
        print("Validation error handling tests passed!")
    
    async def test_websocket_send_functionality(self):
        """Test WebSocket send functionality."""
        print("Testing WebSocket send functionality...")
        
        send_tests = TestWebSocketSendToThread()
        await send_tests.test_send_to_thread_exists()
        await send_tests.test_send_to_thread_with_typed_message()
        
        print("WebSocket send functionality tests passed!")

class TestWebSocketMessageValidationEdgeCases:
    """Test edge cases in WebSocket message validation."""
    
    def test_message_size_limits(self):
        """Test message size limits."""
        # Test very large payload
        large_payload = {"data": "x" * 10000}  # 10KB payload
        message = WebSocketMessageFactory.create_client_message(
            "user_message",
            {
                "content": large_payload["data"],
                "thread_id": "thread123"
            }
        )
        
        assert len(message["payload"]["content"]) == 10000
        assert message["type"] == "user_message"
    
    def test_special_characters_in_messages(self):
        """Test special characters in message fields."""
        special_chars = "!@#$%^&*()_+-=[]{}|;':\",./<>?"
        unicode_chars = "🚀✨🔥💯🎉"
        
        message = WebSocketMessageFactory.create_client_message(
            "user_message",
            {
                "content": f"Test with special chars: {special_chars} and unicode: {unicode_chars}",
                "thread_id": "thread123"
            }
        )
        
        assert special_chars in message["payload"]["content"]
        assert unicode_chars in message["payload"]["content"]
    
    def test_empty_and_null_values(self):
        """Test handling of empty and null values."""
        # Test empty string content
        message = WebSocketMessageFactory.create_client_message(
            "user_message",
            {
                "content": "",
                "thread_id": "thread123"
            }
        )
        
        assert message["payload"]["content"] == ""
        
        # Test with None values in optional fields
        message = WebSocketMessageFactory.create_client_message(
            "start_agent",
            {
                "query": "Test query",
                "user_id": "user123",
                "context": None
            }
        )
        
        assert message["payload"]["context"] is None
    
    def test_numeric_string_conversion(self):
        """Test numeric values in string fields."""
        message = WebSocketMessageFactory.create_client_message(
            "user_message",
            {
                "content": "123456",  # Numeric content as string
                "thread_id": "thread_456"  # Numeric thread ID as string
            }
        )
        
        assert message["payload"]["content"] == "123456"
        assert message["payload"]["thread_id"] == "thread_456"

# Message validation tests are now in dedicated modules
# Import from websocket/ subdirectory for specific test types

if __name__ == "__main__":
    # Run type safety tests
    def run_main_tests():
        """Run main type safety tests."""
        main_tests = TestWebSocketTypeSafetyMain()
        
        print("Running message factory tests...")
        main_tests.test_message_factory_functionality()
        
        print("Running validation error tests...")
        main_tests.test_validation_error_handling()
        
        print("Running complete type safety suite...")
        main_tests.test_complete_type_safety_suite()
        
        print("Running edge case tests...")
        edge_tests = TestWebSocketMessageValidationEdgeCases()
        edge_tests.test_message_size_limits()
        edge_tests.test_special_characters_in_messages()
        edge_tests.test_empty_and_null_values()
        
        print("All type safety tests completed!")
    
    run_main_tests()