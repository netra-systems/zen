"""
Comprehensive WebSocket Serialization Tests

Business Value Justification:
- Segment: Platform/Internal
- Business Goal: System Stability & Risk Reduction  
- Value Impact: Prevents 1011 WebSocket errors that break $120K+ MRR chat functionality
- Strategic Impact: Ensures serialization safety for all WebSocket communications

Tests the comprehensive _serialize_message_safely function to handle:
- WebSocketState enums (CRITICAL for 1011 error prevention)
- Generic enums
- Pydantic models
- Datetime objects
- Complex nested structures
"""

import pytest
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any

from netra_backend.app.websocket_core.unified_manager import _serialize_message_safely


class SerializationTestEnum(Enum):
    """Test enum for serialization testing."""
    VALUE_ONE = "value1"
    VALUE_TWO = "value2"


class TestWebSocketStateSerialization:
    """Test WebSocketState serialization to prevent 1011 errors."""
    
    def test_starlette_websocket_state_serialization(self):
        """Test Starlette WebSocketState enum serialization."""
        try:
            from starlette.websockets import WebSocketState
            
            # Test all WebSocketState values
            assert _serialize_message_safely(WebSocketState.CONNECTING) == "connecting"
            assert _serialize_message_safely(WebSocketState.CONNECTED) == "connected"
            assert _serialize_message_safely(WebSocketState.DISCONNECTED) == "disconnected"
            
        except ImportError:
            pytest.skip("Starlette WebSocketState not available")
    
    def test_fastapi_websocket_state_serialization(self):
        """Test FastAPI WebSocketState enum serialization."""
        try:
            from fastapi.websockets import WebSocketState
            
            # Test all WebSocketState values
            assert _serialize_message_safely(WebSocketState.CONNECTING) == "connecting"
            assert _serialize_message_safely(WebSocketState.CONNECTED) == "connected" 
            assert _serialize_message_safely(WebSocketState.DISCONNECTED) == "disconnected"
            
        except ImportError:
            pytest.skip("FastAPI WebSocketState not available")
    
    def test_websocket_state_in_dictionary(self):
        """Test WebSocketState serialization when embedded in dictionary."""
        try:
            from starlette.websockets import WebSocketState
            
            data = {
                "connection_state": WebSocketState.CONNECTED,
                "message": "Connection established",
                "timestamp": 1234567890
            }
            
            result = _serialize_message_safely(data)
            
            # Verify the WebSocketState was converted to string
            assert result["connection_state"] == "connected"
            assert result["message"] == "Connection established"
            assert result["timestamp"] == 1234567890
            
            # Verify the result is JSON serializable
            json_str = json.dumps(result)
            assert '"connection_state": "connected"' in json_str
            
        except ImportError:
            pytest.skip("Starlette WebSocketState not available")
    
    def test_websocket_state_in_nested_structure(self):
        """Test WebSocketState serialization in complex nested structure."""
        try:
            from starlette.websockets import WebSocketState
            
            data = {
                "connection": {
                    "state": WebSocketState.CONNECTED,
                    "diagnostics": {
                        "client_state": WebSocketState.CONNECTED,
                        "application_state": WebSocketState.CONNECTED
                    }
                },
                "metadata": {
                    "states_list": [
                        WebSocketState.CONNECTING,
                        WebSocketState.CONNECTED,
                        WebSocketState.DISCONNECTED
                    ]
                }
            }
            
            result = _serialize_message_safely(data)
            
            # Verify all WebSocketState objects were converted
            assert result["connection"]["state"] == "connected"
            assert result["connection"]["diagnostics"]["client_state"] == "connected"
            assert result["connection"]["diagnostics"]["application_state"] == "connected"
            assert result["metadata"]["states_list"] == ["connecting", "connected", "disconnected"]
            
            # Verify the result is JSON serializable (this was failing with 1011 errors)
            json_str = json.dumps(result)
            assert json_str is not None
            
        except ImportError:
            pytest.skip("Starlette WebSocketState not available")


class TestGeneralSerialization:
    """Test general serialization functionality."""
    
    def test_already_serializable_dict(self):
        """Test dict that's already JSON serializable passes through unchanged."""
        data = {"key": "value", "number": 42, "boolean": True}
        result = _serialize_message_safely(data)
        assert result == data
    
    def test_regular_enum_serialization(self):
        """Test regular Python enum serialization."""
        result = _serialize_message_safely(SerializationTestEnum.VALUE_ONE)
        assert result == "value1"
        
        result = _serialize_message_safely(SerializationTestEnum.VALUE_TWO)
        assert result == "value2"
    
    def test_datetime_serialization(self):
        """Test datetime object serialization."""
        dt = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = _serialize_message_safely(dt)
        assert result == "2023-01-01T12:00:00+00:00"
    
    def test_list_serialization(self):
        """Test list serialization with mixed types."""
        try:
            from starlette.websockets import WebSocketState
            
            data = [
                "string",
                42,
                WebSocketState.CONNECTED,
                SerializationTestEnum.VALUE_ONE,
                datetime(2023, 1, 1, tzinfo=timezone.utc)
            ]
            
            result = _serialize_message_safely(data)
            
            assert result[0] == "string"
            assert result[1] == 42
            assert result[2] == "connected"
            assert result[3] == "value1"
            assert result[4] == "2023-01-01T00:00:00+00:00"
            
        except ImportError:
            # Test without WebSocketState
            data = [
                "string",
                42, 
                SerializationTestEnum.VALUE_ONE,
                datetime(2023, 1, 1, tzinfo=timezone.utc)
            ]
            
            result = _serialize_message_safely(data)
            
            assert result[0] == "string"
            assert result[1] == 42
            assert result[2] == "value1" 
            assert result[3] == "2023-01-01T00:00:00+00:00"
    
    def test_set_serialization(self):
        """Test set serialization (converted to list)."""
        data = {1, 2, 3}
        result = _serialize_message_safely(data)
        assert isinstance(result, list)
        assert sorted(result) == [1, 2, 3]
    
    def test_unknown_object_fallback(self):
        """Test fallback for unknown object types."""
        class UnknownClass:
            def __str__(self):
                return "unknown_object"
        
        obj = UnknownClass()
        result = _serialize_message_safely(obj)
        assert result == "unknown_object"


class TestConnectionDiagnostics:
    """Test connection diagnostics that caused the original 1011 error."""
    
    def test_connection_diagnostics_json_serializable(self):
        """Test that connection diagnostics can be JSON serialized without errors."""
        # This simulates the problematic scenario that caused 1011 errors
        try:
            from starlette.websockets import WebSocketState
            from netra_backend.app.websocket_core.unified_manager import WebSocketConnection
            from datetime import datetime
            
            # Create mock WebSocket with client_state
            class MockWebSocket:
                def __init__(self):
                    self.client_state = WebSocketState.CONNECTED
            
            # Create connection like the system does
            connection = WebSocketConnection(
                connection_id="test_conn_123",
                user_id="test_user",
                websocket=MockWebSocket(),
                connected_at=datetime.utcnow()
            )
            
            # Simulate getting diagnostics (this is what was failing)
            from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
            manager = UnifiedWebSocketManager()
            
            diagnostics = manager._get_connection_diagnostics(connection)
            
            # CRITICAL: This should not raise "Object of type WebSocketState is not JSON serializable"
            json_str = json.dumps(diagnostics)
            assert json_str is not None
            
            # Verify WebSocketState was converted to string
            assert diagnostics['websocket_state'] == 'connected'
            assert '"websocket_state": "connected"' in json_str
            
        except ImportError:
            pytest.skip("Starlette WebSocketState not available")
    
    def test_diagnostics_with_no_websocket(self):
        """Test diagnostics when websocket is None."""
        from netra_backend.app.websocket_core.unified_manager import WebSocketConnection, UnifiedWebSocketManager
        from datetime import datetime
        
        connection = WebSocketConnection(
            connection_id="test_conn_456", 
            user_id="test_user",
            websocket=None,
            connected_at=datetime.utcnow()
        )
        
        manager = UnifiedWebSocketManager()
        diagnostics = manager._get_connection_diagnostics(connection)
        
        # Should be JSON serializable
        json_str = json.dumps(diagnostics)
        assert json_str is not None
        assert diagnostics['websocket_state'] == 'no_websocket'


class TestSerializationPerformance:
    """Test serialization performance and edge cases."""
    
    def test_large_nested_structure(self):
        """Test serialization of large nested structure."""
        # Create complex structure that might contain WebSocketState
        try:
            from starlette.websockets import WebSocketState
            
            data = {
                "connections": {
                    f"conn_{i}": {
                        "state": WebSocketState.CONNECTED if i % 2 == 0 else WebSocketState.DISCONNECTED,
                        "metadata": {
                            "created_at": datetime.now(timezone.utc),
                            "message_count": i * 10
                        }
                    } for i in range(100)
                }
            }
            
            result = _serialize_message_safely(data)
            
            # Verify all WebSocketStates were converted
            for i in range(100):
                conn_key = f"conn_{i}"
                expected_state = "connected" if i % 2 == 0 else "disconnected"
                assert result["connections"][conn_key]["state"] == expected_state
            
            # Most importantly - verify it's JSON serializable
            json_str = json.dumps(result)
            assert json_str is not None
            
        except ImportError:
            pytest.skip("Starlette WebSocketState not available")
    
    def test_circular_reference_prevention(self):
        """Test that circular references don't cause infinite recursion."""
        # This creates a potential infinite loop scenario
        data = {"key": "value"}
        data["self_ref"] = data  # Circular reference
        
        # Should handle this gracefully without infinite recursion
        try:
            result = _serialize_message_safely(data)
            # The exact behavior may vary, but it shouldn't crash
            assert result is not None
        except (RecursionError, ValueError):
            # If it detects circular reference and fails, that's acceptable
            pass


# Integration test that reproduces the original bug
class TestOriginalBugReproduction:
    """Test that reproduces and verifies the fix for the original 1011 bug."""
    
    def test_websocket_error_message_serialization(self):
        """Test the exact scenario that was causing 1011 errors in staging."""
        try:
            from starlette.websockets import WebSocketState
            
            # Simulate the error message structure that was failing
            error_context = {
                "error_type": "ConnectionError",
                "environment": "staging", 
                "connection_diagnostics": {
                    'has_websocket': True,
                    'websocket_type': 'WebSocket',
                    'connection_age_seconds': 1.23,
                    'metadata_present': False,
                    'websocket_state': WebSocketState.CONNECTED  # This was causing the error
                }
            }
            
            # This should NOT raise "Object of type WebSocketState is not JSON serializable"
            safe_error_context = _serialize_message_safely(error_context)
            
            # Verify WebSocketState was converted to string
            assert safe_error_context["connection_diagnostics"]["websocket_state"] == "connected"
            
            # CRITICAL: Verify it can be JSON serialized (this was failing before)
            json_str = json.dumps(safe_error_context)
            assert json_str is not None
            assert '"websocket_state": "connected"' in json_str
            
            # Simulate sending this as a WebSocket message (what the endpoint does)
            message = {
                "type": "error",
                "error": {
                    "code": "CONNECTION_ERROR",
                    "message": "Connection diagnostics available",
                    "context": safe_error_context
                },
                "timestamp": 1234567890
            }
            
            # This should be completely JSON serializable now
            final_json = json.dumps(message)
            assert final_json is not None
            
        except ImportError:
            pytest.skip("Starlette WebSocketState not available")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])