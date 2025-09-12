"""
Test for Five Whys Fix: create_server_message() missing positional argument 'data'

Business Value Justification:
- Segment: Platform/Internal  
- Business Goal: System Stability & Reliability
- Value Impact: Prevents critical WebSocket connection failures that break chat ($500K+ ARR)
- Strategic Impact: Regression test ensures error handling doesn't break core user flow

Root Cause Addressed: Organizational culture prioritizing velocity over architectural discipline
Fix: Convert ErrorMessage to ServerMessage for proper WebSocket sending
"""

import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime, timezone

from fastapi import WebSocket
from netra_backend.app.routes.websocket_ssot import WebSocketSSOTRouter, WebSocketMode
from netra_backend.app.websocket_core.types import create_server_message


class TestWebSocketErrorHandlingFix:
    """Test suite for Five Whys error handling fix."""

    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        websocket = Mock(spec=WebSocket)
        websocket.send_json = AsyncMock()
        websocket.close = AsyncMock()
        return websocket

    @pytest.fixture
    def handler(self):
        """Create WebSocket handler instance."""
        return WebSocketSSOTRouter()

    @pytest.mark.asyncio
    async def test_handle_connection_error_creates_proper_server_message(self, handler, mock_websocket):
        """
        Test WHY #1 FIX: Verify _handle_connection_error creates ServerMessage instead of ErrorMessage
        
        Root Cause: ErrorMessage passed directly to safe_websocket_send() which expects ServerMessage
        Fix: Convert ErrorMessage data to ServerMessage format with proper 'data' argument
        """
        test_error = Exception("Test connection error")
        test_mode = WebSocketMode.MAIN
        
        with patch('netra_backend.app.routes.websocket_ssot.is_websocket_connected', return_value=True), \
             patch('netra_backend.app.routes.websocket_ssot.safe_websocket_send') as mock_send, \
             patch('netra_backend.app.routes.websocket_ssot.safe_websocket_close') as mock_close:
            
            await handler._handle_connection_error(mock_websocket, test_error, test_mode)
            
            # Verify safe_websocket_send was called with ServerMessage
            assert mock_send.called
            sent_message = mock_send.call_args[0][1]  # Second argument is the message
            
            # Verify it's a ServerMessage with proper structure
            assert hasattr(sent_message, 'type')
            assert hasattr(sent_message, 'data')
            assert hasattr(sent_message, 'timestamp')
            
            # Verify the error data structure
            assert sent_message.type.value == "error"
            assert isinstance(sent_message.data, dict)
            assert "error_code" in sent_message.data
            assert "error_message" in sent_message.data
            assert "details" in sent_message.data
            assert "timestamp" in sent_message.data
            
            # Verify error content
            assert sent_message.data["error_code"] == "CONNECTION_ERROR"
            assert "main mode" in sent_message.data["error_message"]
            assert sent_message.data["details"]["mode"] == "main"
            assert sent_message.data["details"]["error_type"] == "Exception"

    @pytest.mark.asyncio 
    async def test_create_server_message_requires_both_arguments(self):
        """
        Test WHY #1 VALIDATION: Verify create_server_message() requires both msg_type and data
        
        This test confirms the original function signature that was causing the error.
        """
        # Should work with both arguments
        message = create_server_message("test_type", {"test": "data"})
        assert message.type.value == "test_type"
        assert message.data == {"test": "data"}
        
        # Should fail with only one argument
        with pytest.raises(TypeError, match="missing 1 required positional argument: 'data'"):
            create_server_message("test_type")  # Missing 'data' argument

    @pytest.mark.asyncio
    async def test_error_handling_with_different_modes(self, handler, mock_websocket):
        """
        Test WHY #2 FIX: Verify error handling works for all WebSocket modes
        
        Root Cause: No type conversion layer between message types
        Fix: Unified error handling that works across all modes
        """
        test_error = Exception("Multi-mode test error")
        
        for mode in [WebSocketMode.MAIN, WebSocketMode.FACTORY, WebSocketMode.ISOLATED, WebSocketMode.LEGACY]:
            with patch('netra_backend.app.routes.websocket_ssot.is_websocket_connected', return_value=True), \
                 patch('netra_backend.app.routes.websocket_ssot.safe_websocket_send') as mock_send, \
                 patch('netra_backend.app.routes.websocket_ssot.safe_websocket_close'):
                
                await handler._handle_connection_error(mock_websocket, test_error, mode)
                
                # Verify each mode gets proper ServerMessage
                assert mock_send.called
                sent_message = mock_send.call_args[0][1]
                assert hasattr(sent_message, 'type')
                assert hasattr(sent_message, 'data')
                assert sent_message.data["details"]["mode"] == mode.value

    @pytest.mark.asyncio
    async def test_error_handling_when_websocket_disconnected(self, handler, mock_websocket):
        """
        Test WHY #3 FIX: Verify graceful handling when WebSocket already disconnected
        
        Root Cause: Architecture violates interface design principles
        Fix: Proper connection state checking before message sending
        """
        test_error = Exception("Disconnected WebSocket error")
        test_mode = WebSocketMode.MAIN
        
        with patch('netra_backend.app.routes.websocket_ssot.is_websocket_connected', return_value=False), \
             patch('netra_backend.app.routes.websocket_ssot.safe_websocket_send') as mock_send:
            
            await handler._handle_connection_error(mock_websocket, test_error, test_mode)
            
            # Should not attempt to send if WebSocket disconnected
            assert not mock_send.called

    @pytest.mark.asyncio
    async def test_error_handling_cleanup_exception_resilience(self, handler, mock_websocket):
        """
        Test WHY #4 FIX: Verify error handling is resilient to cleanup exceptions
        
        Root Cause: Missing quality validation in development process  
        Fix: Exception handling that doesn't cascade failures
        """
        test_error = Exception("Primary error")
        test_mode = WebSocketMode.MAIN
        
        with patch('netra_backend.app.routes.websocket_ssot.is_websocket_connected', return_value=True), \
             patch('netra_backend.app.routes.websocket_ssot.safe_websocket_send', side_effect=Exception("Send failed")), \
             patch('netra_backend.app.routes.websocket_ssot.logger') as mock_logger:
            
            # Should not raise exception even if cleanup fails
            await handler._handle_connection_error(mock_websocket, test_error, test_mode)
            
            # Should log the cleanup error
            assert any("Error during cleanup" in str(call) for call in mock_logger.error.call_args_list)

    @pytest.mark.asyncio
    async def test_server_message_serialization_compatibility(self):
        """
        Test WHY #5 FIX: Verify ServerMessage is properly serializable for WebSocket sending
        
        Root Cause: Organization values feature velocity over engineering excellence
        Fix: Ensure all message types are WebSocket-compatible by design
        """
        error_data = {
            "error_code": "CONNECTION_ERROR",
            "error_message": "Test connection error in main mode",
            "details": {"error_type": "Exception", "mode": "main"},
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        server_message = create_server_message("error", error_data)
        
        # Should be JSON serializable
        message_dict = {
            "type": server_message.type.value,
            "data": server_message.data,
            "timestamp": server_message.timestamp,
            "correlation_id": server_message.correlation_id
        }
        
        # This should not raise an exception
        json_str = json.dumps(message_dict)
        assert isinstance(json_str, str)
        assert "CONNECTION_ERROR" in json_str
        assert "main mode" in json_str

    def test_five_whys_documentation_completeness(self):
        """
        Meta-test: Verify Five Whys analysis is properly documented in fix
        
        Validates that the organizational learning from root cause analysis
        is preserved in the code for future developers.
        """
        import inspect
        
        # Read the source code of _handle_connection_error
        source_lines = inspect.getsourcelines(WebSocketSSOTRouter._handle_connection_error)[0]
        source_code = ''.join(source_lines)
        
        # Verify Five Whys levels are documented in comments
        required_documentation = [
            "FIVE WHYS FIX",
            "Root Cause: Organizational culture prioritizing velocity over architectural discipline",
            "WHY #1:", "WHY #2:", "WHY #3:", "WHY #4:", "WHY #5:"
        ]
        
        for doc_element in required_documentation:
            assert doc_element in source_code, f"Missing Five Whys documentation: {doc_element}"

    @pytest.mark.integration
    async def test_end_to_end_error_recovery(self, handler, mock_websocket):
        """
        Integration test: Complete error  ->  recovery  ->  prevention cycle
        
        Validates that the Five Whys fix addresses the complete error scenario
        from initial failure through proper error communication to client.
        """
        primary_error = Exception("Simulated connection failure")
        test_mode = WebSocketMode.MAIN
        
        # Capture all the steps in error handling
        send_calls = []
        close_calls = []
        
        async def capture_send(ws, message):
            send_calls.append(message)
            return True
            
        async def capture_close(ws, code, reason):
            close_calls.append((code, reason))
        
        with patch('netra_backend.app.routes.websocket_ssot.is_websocket_connected', return_value=True), \
             patch('netra_backend.app.routes.websocket_ssot.safe_websocket_send', side_effect=capture_send), \
             patch('netra_backend.app.routes.websocket_ssot.safe_websocket_close', side_effect=capture_close):
            
            await handler._handle_connection_error(mock_websocket, primary_error, test_mode)
            
            # Verify complete error handling flow
            assert len(send_calls) == 1, "Should send exactly one error message"
            assert len(close_calls) == 1, "Should close connection exactly once"
            
            # Verify error message structure
            error_message = send_calls[0]
            assert error_message.type.value == "error"
            assert "CONNECTION_ERROR" in error_message.data["error_code"]
            
            # Verify connection close
            close_code, close_reason = close_calls[0]
            assert close_code == 1011  # Internal server error
            assert "main mode error" in close_reason


# Prevention Measures Test Suite

class TestErrorHandlingPrevention:
    """Tests that verify systemic improvements to prevent similar errors."""

    def test_all_create_server_message_calls_have_data_argument(self):
        """
        Regression Prevention: Scan for any create_server_message calls missing data argument
        
        This test would be expanded to scan the entire codebase for similar patterns.
        """
        import re
        import os
        
        # Read the websocket_ssot.py file
        file_path = "/Users/rindhujajohnson/Netra/GitHub/netra-apex/netra_backend/app/routes/websocket_ssot.py"
        with open(file_path, 'r') as f:
            content = f.read()
        
        # Find all create_server_message calls
        pattern = r'create_server_message\([^)]+\)'
        matches = re.findall(pattern, content)
        
        for match in matches:
            # Each call should have at least 2 arguments (msg_type, data)
            # Count commas to estimate argument count
            comma_count = match.count(',')
            assert comma_count >= 1, f"create_server_message call appears to be missing data argument: {match}"

    def test_websocket_message_type_consistency(self):
        """
        Architectural Validation: Ensure all WebSocket message types follow consistent patterns
        
        Prevents WHY #3 (Architecture violates interface design principles)
        """
        from netra_backend.app.websocket_core.types import ServerMessage, ErrorMessage, WebSocketMessage
        
        # All message types should have consistent required fields
        message_types = [ServerMessage, ErrorMessage, WebSocketMessage]
        
        for msg_type in message_types:
            # Each should have timestamp field
            assert hasattr(msg_type, '__annotations__'), f"{msg_type} should have type annotations"
            annotations = msg_type.__annotations__
            assert 'timestamp' in annotations, f"{msg_type} should have timestamp field"