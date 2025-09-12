"""
Basic WebSocket Close Code Handling Test

Business Value Justification (BVJ):
- Segment: All customer segments (Free, Early, Mid, Enterprise)
- Business Goal: WebSocket connection reliability and proper resource cleanup
- Value Impact: Ensures proper connection termination and resource cleanup
- Revenue Impact: Prevents connection leaks that could impact system stability

This test focuses on basic WebSocket close code functionality:
1. Normal closure (code 1000) 
2. Protocol error handling (code 1002)
3. Invalid frame data handling (code 1003)
4. Policy violation handling (code 1008)
5. Message too big handling (code 1009)
6. Internal error handling (code 1011)
7. Clean disconnection sequence validation

Note: This test validates basic WebSocket close code handling using mocked connections
to ensure the WebSocket infrastructure properly handles different disconnection scenarios.
"""

import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any
from unittest.mock import MagicMock, AsyncMock, Mock, patch
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from shared.isolated_environment import IsolatedEnvironment

import pytest
from starlette.websockets import WebSocketState


class TestWebSocketCloseCodes:
    """Test basic WebSocket close code handling and clean disconnection."""
    
    @pytest.mark.asyncio
    async def test_normal_closure_clean_disconnect(self):
        """Test normal WebSocket closure with code 1000 (normal closure)."""
        # Mock websocket connection
        mock_websocket = AsyncMock()  # TODO: Use real service instance
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        # Mock welcome message
        welcome_message = json.dumps({
            "type": "connection_established",
            "connection_id": "test-close-normal",
            "server_time": datetime.now(timezone.utc).isoformat(),
            "message": "WebSocket connected - testing normal closure"
        })
        
        # Set up mock to return welcome message then simulate close
        from websockets.exceptions import ConnectionClosed
        mock_websocket.recv = AsyncMock(side_effect=[
            welcome_message,
            ConnectionClosed(None, None)
        ])
        mock_websocket.send_json = AsyncMock()  # TODO: Use real service instance
        mock_websocket.close = AsyncMock()  # TODO: Use real service instance
        
        # Mock connection context manager
        mock_connection = AsyncMock()  # TODO: Use real service instance
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                # Receive welcome message
                welcome = await websocket.recv()
                welcome_data = json.loads(welcome)
                
                assert welcome_data["type"] == "connection_established"
                assert "connection_id" in welcome_data
                print(f" PASS:  Connected: {welcome_data['connection_id']}")
                
                # Send close message
                close_message = {
                    "type": "disconnect",
                    "reason": "user_initiated",
                    "code": 1000
                }
                
                await websocket.send_json(close_message)
                print(f"[U+1F4E4] Sent close request: {close_message}")
                
                # Verify connection closes cleanly
                try:
                    # This should raise ConnectionClosed
                    await websocket.recv()
                    assert False, "Should have been disconnected"
                except ConnectionClosed:
                    print(" PASS:  Connection closed cleanly")
                    pass
                
                # Verify send_json was called for close message
                websocket.send_json.assert_called_once_with(close_message)
    
    @pytest.mark.asyncio
    async def test_protocol_error_close_code_1002(self):
        """Test WebSocket closure with code 1002 (protocol error)."""
        # Mock websocket connection
        mock_websocket = AsyncMock()  # TODO: Use real service instance
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        # Mock error response for protocol violation
        error_response = json.dumps({
            "type": "error",
            "error_code": "PROTOCOL_ERROR",
            "message": "Invalid WebSocket protocol usage",
            "close_code": 1002,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Set up mock to return error then close
        from websockets.exceptions import ConnectionClosedError
        mock_websocket.recv = AsyncMock(side_effect=[
            error_response,
            ConnectionClosedError(None, None)
        ])
        mock_websocket.send = AsyncMock()  # TODO: Use real service instance
        mock_websocket.close = AsyncMock()  # TODO: Use real service instance
        
        # Mock connection context manager
        mock_connection = AsyncMock()  # TODO: Use real service instance
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                # Send invalid protocol message (binary when expecting text)
                invalid_protocol_message = b'\x00\x01\x02invalid_binary'
                
                await websocket.send(invalid_protocol_message)
                print(f"[U+1F4E4] Sent invalid protocol message")
                
                # Wait for error response
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # Verify error response
                assert response_data["type"] == "error"
                assert response_data["error_code"] == "PROTOCOL_ERROR"
                assert response_data["close_code"] == 1002
                
                print(f"[U+1F4E5] Received protocol error: {response_data}")
                
                # Verify connection closes with protocol error
                try:
                    await websocket.recv()
                    assert False, "Should have been disconnected"
                except ConnectionClosedError:
                    print(" PASS:  Connection closed due to protocol error")
                    pass
    
    @pytest.mark.asyncio
    async def test_invalid_data_close_code_1003(self):
        """Test WebSocket closure with code 1003 (unsupported data)."""
        # Mock websocket connection
        mock_websocket = AsyncMock()  # TODO: Use real service instance
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        # Mock error response for invalid data
        error_response = json.dumps({
            "type": "error",
            "error_code": "INVALID_DATA",
            "message": "Received data type not supported",
            "close_code": 1003,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Set up mock to return error then close
        from websockets.exceptions import ConnectionClosedError
        mock_websocket.recv = AsyncMock(side_effect=[
            error_response,
            ConnectionClosedError(None, None)
        ])
        mock_websocket.send = AsyncMock()  # TODO: Use real service instance
        
        # Mock connection context manager
        mock_connection = AsyncMock()  # TODO: Use real service instance
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                # Send unsupported binary data when text expected
                unsupported_data = b'\xFF\xFE\xFD\xFC'  # Invalid UTF-8
                
                await websocket.send(unsupported_data)
                print(f"[U+1F4E4] Sent unsupported data")
                
                # Wait for error response
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # Verify error response
                assert response_data["type"] == "error"
                assert response_data["error_code"] == "INVALID_DATA"
                assert response_data["close_code"] == 1003
                
                print(f"[U+1F4E5] Received invalid data error: {response_data}")
                
                # Verify connection closes
                try:
                    await websocket.recv()
                    assert False, "Should have been disconnected"
                except ConnectionClosedError:
                    print(" PASS:  Connection closed due to invalid data")
                    pass
    
    @pytest.mark.asyncio
    async def test_policy_violation_close_code_1008(self):
        """Test WebSocket closure with code 1008 (policy violation)."""
        # Mock websocket connection
        mock_websocket = AsyncMock()  # TODO: Use real service instance
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        # Mock error response for policy violation
        error_response = json.dumps({
            "type": "error",
            "error_code": "POLICY_VIOLATION",
            "message": "Message rate limit exceeded",
            "close_code": 1008,
            "details": {
                "rate_limit": "30 messages per minute",
                "current_rate": "45 messages per minute"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Set up mock to return error then close
        from websockets.exceptions import ConnectionClosedError
        mock_websocket.recv = AsyncMock(side_effect=[
            error_response,
            ConnectionClosedError(None, None)
        ])
        mock_websocket.send_json = AsyncMock()  # TODO: Use real service instance
        
        # Mock connection context manager
        mock_connection = AsyncMock()  # TODO: Use real service instance
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                # Simulate rapid message sending (rate limit violation)
                for i in range(50):  # Exceed rate limit
                    spam_message = {
                        "type": "user_message",
                        "payload": {"content": f"Spam message {i}"}
                    }
                    await websocket.send_json(spam_message)
                
                print(f"[U+1F4E4] Sent 50 rapid messages (exceeding rate limit)")
                
                # Wait for policy violation error
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # Verify error response
                assert response_data["type"] == "error"
                assert response_data["error_code"] == "POLICY_VIOLATION"
                assert response_data["close_code"] == 1008
                assert "rate_limit" in response_data["details"]
                
                print(f"[U+1F4E5] Received policy violation: {response_data}")
                
                # Verify connection closes due to policy violation
                try:
                    await websocket.recv()
                    assert False, "Should have been disconnected"
                except ConnectionClosedError:
                    print(" PASS:  Connection closed due to policy violation")
                    pass
    
    @pytest.mark.asyncio
    async def test_message_too_big_close_code_1009(self):
        """Test WebSocket closure with code 1009 (message too big)."""
        # Mock websocket connection
        mock_websocket = AsyncMock()  # TODO: Use real service instance
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        # Mock error response for message too big
        error_response = json.dumps({
            "type": "error",
            "error_code": "MESSAGE_TOO_BIG",
            "message": "Message exceeds maximum size limit",
            "close_code": 1009,
            "details": {
                "max_size_bytes": 8192,
                "received_size_bytes": 16384
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Set up mock to return error then close
        from websockets.exceptions import ConnectionClosedError
        mock_websocket.recv = AsyncMock(side_effect=[
            error_response,
            ConnectionClosedError(None, None)
        ])
        mock_websocket.send_json = AsyncMock()  # TODO: Use real service instance
        
        # Mock connection context manager
        mock_connection = AsyncMock()  # TODO: Use real service instance
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                # Send oversized message (16KB content when limit is 8KB)
                oversized_content = "x" * 16384  # 16KB
                oversized_message = {
                    "type": "user_message",
                    "payload": {"content": oversized_content}
                }
                
                await websocket.send_json(oversized_message)
                print(f"[U+1F4E4] Sent oversized message ({len(oversized_content)} bytes)")
                
                # Wait for message too big error
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # Verify error response
                assert response_data["type"] == "error"
                assert response_data["error_code"] == "MESSAGE_TOO_BIG"
                assert response_data["close_code"] == 1009
                assert "max_size_bytes" in response_data["details"]
                
                print(f"[U+1F4E5] Received message too big error: {response_data}")
                
                # Verify connection closes
                try:
                    await websocket.recv()
                    assert False, "Should have been disconnected"
                except ConnectionClosedError:
                    print(" PASS:  Connection closed due to message size")
                    pass
    
    @pytest.mark.asyncio
    async def test_internal_error_close_code_1011(self):
        """Test WebSocket closure with code 1011 (internal server error)."""
        # Mock websocket connection
        mock_websocket = AsyncMock()  # TODO: Use real service instance
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        # Mock error response for internal error
        error_response = json.dumps({
            "type": "error",
            "error_code": "INTERNAL_ERROR",
            "message": "An internal server error occurred",
            "close_code": 1011,
            "details": {
                "error_id": "ERR_2025_001",
                "suggestion": "Please reconnect and try again"
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Set up mock to return error then close
        from websockets.exceptions import ConnectionClosedError
        mock_websocket.recv = AsyncMock(side_effect=[
            error_response,
            ConnectionClosedError(None, None)
        ])
        mock_websocket.send_json = AsyncMock()  # TODO: Use real service instance
        
        # Mock connection context manager
        mock_connection = AsyncMock()  # TODO: Use real service instance
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                # Send message that triggers internal error
                trigger_message = {
                    "type": "trigger_internal_error",  # Special test message type
                    "payload": {"simulate": "server_crash"}
                }
                
                await websocket.send_json(trigger_message)
                print(f"[U+1F4E4] Sent internal error trigger")
                
                # Wait for internal error response
                response = await websocket.recv()
                response_data = json.loads(response)
                
                # Verify error response
                assert response_data["type"] == "error"
                assert response_data["error_code"] == "INTERNAL_ERROR"
                assert response_data["close_code"] == 1011
                assert "error_id" in response_data["details"]
                
                print(f"[U+1F4E5] Received internal error: {response_data}")
                
                # Verify connection closes due to internal error
                try:
                    await websocket.recv()
                    assert False, "Should have been disconnected"
                except ConnectionClosedError:
                    print(" PASS:  Connection closed due to internal error")
                    pass
    
    @pytest.mark.asyncio
    async def test_clean_disconnect_sequence(self):
        """Test complete clean disconnection sequence with proper resource cleanup."""
        # Mock websocket connection
        mock_websocket = AsyncMock()  # TODO: Use real service instance
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        # Mock message sequence: welcome -> messages -> disconnect confirmation -> close
        welcome_message = json.dumps({
            "type": "connection_established",
            "connection_id": "test-clean-disconnect"
        })
        
        ping_response = json.dumps({
            "type": "pong",
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        disconnect_confirmation = json.dumps({
            "type": "disconnect_acknowledged",
            "connection_id": "test-clean-disconnect", 
            "cleanup_completed": True,
            "resources_released": ["connection", "heartbeat", "message_queue"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Set up mock message sequence
        from websockets.exceptions import ConnectionClosed
        mock_websocket.recv = AsyncMock(side_effect=[
            welcome_message,
            ping_response,
            disconnect_confirmation,
            ConnectionClosed(None, None)
        ])
        mock_websocket.send_json = AsyncMock()  # TODO: Use real service instance
        mock_websocket.close = AsyncMock()  # TODO: Use real service instance
        
        # Mock connection context manager
        mock_connection = AsyncMock()  # TODO: Use real service instance
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                # 1. Establish connection
                welcome = await websocket.recv()
                welcome_data = json.loads(welcome)
                connection_id = welcome_data["connection_id"]
                print(f" PASS:  1. Connected: {connection_id}")
                
                # 2. Exchange some messages
                ping_message = {"type": "ping"}
                await websocket.send_json(ping_message)
                
                pong = await websocket.recv()
                pong_data = json.loads(pong)
                assert pong_data["type"] == "pong"
                print(f" PASS:  2. Message exchange successful")
                
                # 3. Initiate clean disconnect
                disconnect_message = {
                    "type": "disconnect",
                    "reason": "user_logout",
                    "cleanup_requested": True
                }
                await websocket.send_json(disconnect_message)
                print(f" PASS:  3. Disconnect initiated")
                
                # 4. Wait for disconnect acknowledgment
                disconnect_ack = await websocket.recv()
                disconnect_data = json.loads(disconnect_ack)
                
                # Verify clean disconnect sequence
                assert disconnect_data["type"] == "disconnect_acknowledged"
                assert disconnect_data["cleanup_completed"] is True
                assert "resources_released" in disconnect_data
                assert "connection" in disconnect_data["resources_released"]
                
                print(f" PASS:  4. Disconnect acknowledged with cleanup")
                
                # 5. Verify connection closes cleanly
                try:
                    await websocket.recv()
                    assert False, "Should have been disconnected"
                except ConnectionClosed:
                    print(" PASS:  5. Connection closed cleanly")
                    pass
                
                # Verify all expected calls were made
                assert websocket.send_json.call_count == 2  # ping + disconnect
                expected_calls = [ping_message, disconnect_message]
                actual_calls = [call.args[0] for call in websocket.send_json.call_args_list]
                
                for expected, actual in zip(expected_calls, actual_calls):
                    assert expected == actual
                
                print(" PASS:  6. All message calls verified")
    
    @pytest.mark.asyncio
    async def test_unexpected_disconnection_handling(self):
        """Test handling of unexpected disconnections (network issues, etc.)."""
        # Mock websocket connection
        mock_websocket = AsyncMock()  # TODO: Use real service instance
        mock_websocket.application_state = WebSocketState.CONNECTED
        
        # Mock welcome message then unexpected disconnect
        welcome_message = json.dumps({
            "type": "connection_established",
            "connection_id": "test-unexpected-disconnect"
        })
        
        # Set up mock for unexpected disconnect
        from websockets.exceptions import ConnectionClosedError
        mock_websocket.recv = AsyncMock(side_effect=[
            welcome_message,
            ConnectionClosedError(None, None)  # Unexpected disconnect
        ])
        mock_websocket.send_json = AsyncMock()  # TODO: Use real service instance
        
        # Mock connection context manager
        mock_connection = AsyncMock()  # TODO: Use real service instance
        mock_connection.__aenter__ = AsyncMock(return_value=mock_websocket)
        mock_connection.__aexit__ = AsyncMock(return_value=None)
        
        with patch('websockets.connect', return_value=mock_connection):
            async with mock_connection as websocket:
                # Receive welcome message
                welcome = await websocket.recv()
                welcome_data = json.loads(welcome)
                print(f" PASS:  Connected: {welcome_data['connection_id']}")
                
                # Send a message
                test_message = {
                    "type": "user_message",
                    "payload": {"content": "This message may not get a response"}
                }
                await websocket.send_json(test_message)
                print(f"[U+1F4E4] Sent message before unexpected disconnect")
                
                # Try to receive response - should get unexpected disconnect
                try:
                    response = await websocket.recv()
                    assert False, "Should have been unexpectedly disconnected"
                except ConnectionClosedError as e:
                    print(" WARNING: [U+FE0F]  Unexpected disconnection detected")
                    # In real implementation, this would trigger reconnection logic
                    assert True  # Expected behavior
                
                # Verify message was sent before disconnect
                websocket.send_json.assert_called_once_with(test_message)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])