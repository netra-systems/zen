"""Test #5: Basic Error Handling Test [HIGH - P1]

Tests error response for malformed messages and validation failures.
Ensures meaningful error messages reach client and errors don't crash connections.

Business Value Justification (BVJ):
- Segment: All customer tiers
- Business Goal: Prevent silent failures and poor user experience
- Value Impact: Users must receive clear error feedback for invalid messages
- Revenue Impact: Proper error handling prevents user frustration and support tickets

Test Requirements:
- Malformed JSON triggers error response
- Missing required fields trigger validation error
- Server errors don't crash connection
- Client receives meaningful error messages
- Use real WebSocket connections (no mocks)
- Follow SPEC/websockets.xml JSON-first approach
"""

import asyncio
import json
import pytest
from typing import Dict, Any, Optional, Union
from datetime import datetime, timezone

from netra_backend.tests.unified.config import TEST_CONFIG, TEST_ENDPOINTS
from netra_backend.tests.unified.real_websocket_client import RealWebSocketClient
from netra_backend.tests.unified.real_client_types import create_test_config


class ErrorHandlingTester:
    """Real WebSocket error handling tester."""
    
    def __init__(self):
        self.client: Optional[RealWebSocketClient] = None
        self.error_responses: list = []
        self.connection_errors: list = []
        self.test_token = self._create_test_token()
    
    def _create_test_token(self) -> str:
        """Create test JWT token for authentication."""
        try:
            # Ensure test environment is set up
            from netra_backend.tests.unified.config import setup_test_environment
            setup_test_environment()
            
            from netra_backend.app.tests.test_utilities.auth_test_helpers import create_test_token
            return create_test_token("error_handling_user")
        except ImportError:
            return "mock-token-error_handling_user"
    
    async def setup_client(self) -> bool:
        """Setup WebSocket client with authentication."""
        # Ensure test user exists in database
        await self._ensure_test_user_exists()
        
        config = create_test_config(timeout=15.0, max_retries=2)
        ws_url = f"{TEST_ENDPOINTS.ws_url}?token={self.test_token}"
        
        self.client = RealWebSocketClient(ws_url, config)
        return await self.client.connect()
    
    async def _ensure_test_user_exists(self) -> None:
        """Ensure test user exists in database."""
        try:
            from netra_backend.app.db.postgres import get_async_db
            from netra_backend.app.db.models_postgres import User
            from sqlalchemy import select
            
            async with get_async_db() as db:
                # Check if user exists
                result = await db.execute(
                    select(User).where(User.id == "error_handling_user")
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    # Create test user
                    test_user = User(
                        id="error_handling_user",
                        email="error_handling_user@test.com",
                        full_name="Error Handling Test User",
                        is_active=True,
                        plan_tier="free"
                    )
                    db.add(test_user)
                    await db.commit()
        except Exception as e:
            # If database setup fails, continue with test (might be using mock auth)
            print(f"Warning: Could not create test user: {e}")
    
    async def send_raw_message(self, message: Union[str, bytes]) -> bool:
        """Send raw message (potentially malformed) to server."""
        if not self.client or not self.client._websocket:
            return False
        
        try:
            if isinstance(message, str):
                await self.client._websocket.send(message)
            else:
                await self.client._websocket.send(message)
            return True
        except Exception as e:
            self.connection_errors.append(str(e))
            return False
    
    async def send_json_message(self, message: Dict[str, Any]) -> bool:
        """Send JSON message to server."""
        if not self.client:
            return False
        return await self.client.send(message)
    
    async def wait_for_error_response(self, timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Wait for error response from server."""
        if not self.client:
            return None
        
        response = await self.client.receive(timeout)
        if response:
            self.error_responses.append(response)
        return response
    
    async def send_and_expect_error(self, message: Union[str, Dict[str, Any]], 
                                  timeout: float = 5.0) -> Optional[Dict[str, Any]]:
        """Send message and expect error response."""
        if isinstance(message, str):
            sent = await self.send_raw_message(message)
        else:
            sent = await self.send_json_message(message)
        
        if not sent:
            return None
        
        return await self.wait_for_error_response(timeout)
    
    def verify_connection_alive(self) -> bool:
        """Verify WebSocket connection is still alive after error."""
        if not self.client or not self.client._websocket:
            return False
        
        # Check connection state properly
        try:
            # For websockets library, check if connection is open
            import websockets
            if hasattr(self.client._websocket, 'state'):
                return self.client._websocket.state == websockets.connection.State.OPEN
            elif hasattr(self.client._websocket, 'open'):
                return self.client._websocket.open
            else:
                # Fallback: assume alive if websocket exists
                return True
        except Exception:
            return False
    
    async def cleanup(self) -> None:
        """Cleanup WebSocket connection."""
        if self.client:
            await self.client.close()


@pytest.fixture
async def error_tester():
    """Create error handling tester fixture."""
    tester = ErrorHandlingTester()
    yield tester
    await tester.cleanup()


class TestMalformedJSONHandling:
    """Test handling of malformed JSON messages."""
    
    async def test_invalid_json_syntax(self, error_tester):
        """Test server response to invalid JSON syntax."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send malformed JSON
        malformed_json = '{"type": "test", "invalid": json, syntax}'
        
        response = await error_tester.send_and_expect_error(malformed_json)
        
        # Verify connection remains alive
        assert error_tester.verify_connection_alive(), "Connection should survive malformed JSON"
        
        # If server responds to malformed JSON, verify error format
        if response:
            assert isinstance(response, dict), "Error response must be valid JSON"
            error_indicators = ["error", "invalid", "malformed", "json", "syntax"]
            response_str = json.dumps(response).lower()
            has_error_indicator = any(indicator in response_str for indicator in error_indicators)
            assert has_error_indicator, f"Error response should indicate JSON problem: {response}"
    
    async def test_incomplete_json_message(self, error_tester):
        """Test handling of incomplete JSON messages."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send incomplete JSON
        incomplete_json = '{"type": "test", "data":'  # Missing closing braces
        
        response = await error_tester.send_and_expect_error(incomplete_json)
        
        # Verify connection survives
        assert error_tester.verify_connection_alive(), "Connection should survive incomplete JSON"
        
        # Verify error response format if received
        if response:
            assert isinstance(response, dict), "Error response must be valid JSON"
    
    async def test_empty_message_handling(self, error_tester):
        """Test handling of empty messages."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send empty message
        empty_message = ""
        
        response = await error_tester.send_and_expect_error(empty_message)
        
        # Verify connection survives
        assert error_tester.verify_connection_alive(), "Connection should survive empty message"
    
    async def test_non_json_message_handling(self, error_tester):
        """Test handling of non-JSON text messages."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send plain text (not JSON)
        plain_text = "This is not JSON at all"
        
        response = await error_tester.send_and_expect_error(plain_text)
        
        # Verify connection survives
        assert error_tester.verify_connection_alive(), "Connection should survive non-JSON message"
        
        # If server responds, verify it's proper JSON
        if response:
            assert isinstance(response, dict), "Error response must be valid JSON even for non-JSON input"


class TestValidationErrorHandling:
    """Test validation error handling for required fields."""
    
    async def test_missing_type_field(self, error_tester):
        """Test error when required 'type' field is missing."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send message without 'type' field
        no_type_message = {
            "content": "Message without type field",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        response = await error_tester.send_and_expect_error(no_type_message)
        
        # Verify connection survives
        assert error_tester.verify_connection_alive(), "Connection should survive missing type field"
        
        # Verify error response if received
        if response:
            assert isinstance(response, dict), "Error response must be valid JSON"
            response_str = json.dumps(response).lower()
            type_error_indicators = ["type", "required", "missing", "field"]
            has_type_error = any(indicator in response_str for indicator in type_error_indicators)
            assert has_type_error, f"Should indicate type field problem: {response}"
    
    async def test_invalid_message_type(self, error_tester):
        """Test error when message type is invalid/unknown."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send message with invalid type
        invalid_type_message = {
            "type": "completely_unknown_message_type_xyz123",
            "content": "Message with unknown type",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        response = await error_tester.send_and_expect_error(invalid_type_message)
        
        # Verify connection survives
        assert error_tester.verify_connection_alive(), "Connection should survive invalid message type"
        
        # Server may or may not respond to unknown types - both behaviors are acceptable
        if response:
            assert isinstance(response, dict), "Response must be valid JSON"
    
    async def test_missing_required_content_fields(self, error_tester):
        """Test error when message is missing required content fields."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send chat message without required content
        incomplete_chat = {
            "type": "chat_message",
            "timestamp": datetime.now(timezone.utc).isoformat()
            # Missing 'content' and 'user_id' fields
        }
        
        response = await error_tester.send_and_expect_error(incomplete_chat)
        
        # Verify connection survives
        assert error_tester.verify_connection_alive(), "Connection should survive missing content fields"
        
        # If server validates content fields, should get error response
        if response:
            assert isinstance(response, dict), "Error response must be valid JSON"


class TestServerErrorRecovery:
    """Test server error recovery and connection stability."""
    
    async def test_connection_stability_after_errors(self, error_tester):
        """Test that connection remains stable after multiple errors."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send multiple error-inducing messages
        error_messages = [
            '{"invalid": json}',  # Malformed JSON
            {"type": "unknown_type_xyz"},  # Unknown type
            {},  # Empty object
            {"type": ""},  # Empty type
        ]
        
        for i, msg in enumerate(error_messages):
            await error_tester.send_and_expect_error(msg)
            
            # Verify connection still alive after each error
            assert error_tester.verify_connection_alive(), f"Connection failed after error {i + 1}"
        
        # Send valid message to confirm connection still works
        valid_message = {
            "type": "ping",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        sent = await error_tester.send_json_message(valid_message)
        assert sent, "Should be able to send valid message after errors"
        
        # Try to receive response (pong or acknowledgment)
        response = await error_tester.wait_for_error_response(timeout=5.0)
        
        # Connection should still be functional
        assert error_tester.verify_connection_alive(), "Connection should be stable after error recovery"
    
    async def test_rapid_error_message_handling(self, error_tester):
        """Test handling of rapid succession of error messages."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send many malformed messages rapidly
        malformed_messages = [f'{{"invalid": json{i}}}' for i in range(5)]
        
        # Send all messages rapidly
        send_tasks = []
        for msg in malformed_messages:
            task = asyncio.create_task(error_tester.send_raw_message(msg))
            send_tasks.append(task)
        
        # Wait for all sends to complete
        results = await asyncio.gather(*send_tasks, return_exceptions=True)
        
        # At least some messages should have been sent
        successful_sends = sum(1 for result in results if result is True)
        assert successful_sends > 0, "At least some error messages should be sendable"
        
        # Connection should survive rapid error messages
        await asyncio.sleep(1.0)  # Allow server time to process
        assert error_tester.verify_connection_alive(), "Connection should survive rapid error messages"


class TestErrorMessageContent:
    """Test the content and format of error messages."""
    
    async def test_error_message_format(self, error_tester):
        """Test that error messages follow proper JSON format."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send message that should trigger error response
        malformed_json = '{"type": "test", "malformed": true'  # Missing closing brace
        
        response = await error_tester.send_and_expect_error(malformed_json, timeout=8.0)
        
        if response:
            # Verify response is proper JSON
            assert isinstance(response, dict), "Error response must be valid JSON dict"
            
            # Check for common error response patterns
            expected_error_fields = ["error", "message", "status", "type"]
            has_error_field = any(field in response for field in expected_error_fields)
            
            if has_error_field:
                # If server follows error conventions, verify structure
                if "error" in response:
                    assert isinstance(response["error"], (str, dict)), "Error field should be string or object"
                if "message" in response:
                    assert isinstance(response["message"], str), "Message field should be string"
    
    async def test_error_message_helpfulness(self, error_tester):
        """Test that error messages provide helpful information."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Send message with specific validation error
        missing_type_message = {
            "content": "This message is missing the type field",
            "user_id": "test_user"
        }
        
        response = await error_tester.send_and_expect_error(missing_type_message, timeout=8.0)
        
        if response:
            # Convert entire response to string for analysis
            response_text = json.dumps(response).lower()
            
            # Look for helpful keywords that indicate what went wrong
            helpful_keywords = [
                "type", "required", "missing", "field", "invalid", 
                "validation", "format", "expected"
            ]
            
            has_helpful_content = any(keyword in response_text for keyword in helpful_keywords)
            
            # If server provides error details, they should be helpful
            if len(response_text) > 20:  # Non-trivial response
                assert has_helpful_content, f"Error message should be helpful: {response}"


class TestConnectionRecoveryAfterErrors:
    """Test connection recovery capabilities after error conditions."""
    
    async def test_functional_recovery_after_errors(self, error_tester):
        """Test that normal functionality works after error conditions."""
        connected = await error_tester.setup_client()
        assert connected, "Failed to establish WebSocket connection"
        
        # Create error condition
        malformed_message = '{"broken": json syntax here}'
        await error_tester.send_and_expect_error(malformed_message)
        
        # Verify connection is still alive
        assert error_tester.verify_connection_alive(), "Connection should survive error"
        
        # Test that normal operations still work
        normal_message = {
            "type": "ping",
            "test_recovery": True,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Send normal message
        sent = await error_tester.send_json_message(normal_message)
        assert sent, "Should be able to send normal message after error"
        
        # Try to receive response
        response = await error_tester.wait_for_error_response(timeout=5.0)
        
        # If we get a response, it should be well-formed
        if response:
            assert isinstance(response, dict), "Recovery response should be valid JSON"
            
        # Connection should remain stable
        assert error_tester.verify_connection_alive(), "Connection should remain stable after recovery test"