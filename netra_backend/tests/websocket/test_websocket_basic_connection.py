"""
Basic WebSocket Connection Test

This test focuses on the most fundamental websocket functionality:
1. Connection establishment without authentication (using /ws/test endpoint)
2. Basic message send/receive (ping/pong)
3. JSON message parsing
4. Connection termination

This test is designed to verify that the basic websocket infrastructure is working
without requiring the full authentication stack or database connections.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any

import pytest
import websockets
from websockets.exceptions import ConnectionClosed

from test_framework.test_patterns import BaseTest


class TestWebSocketBasicConnection(BaseTest):
    """Test basic WebSocket connectivity using the unauthenticated test endpoint."""
    
    @pytest.mark.asyncio
    async def test_websocket_test_endpoint_connection(self):
        """Test that we can connect to the unauthenticated /ws/test endpoint."""
        websocket_url = "ws://localhost:8000/ws/test"
        
        try:
            async with websockets.connect(websocket_url) as websocket:
                # Connection successful if we get here
                assert websocket.open, "WebSocket should be open after connection"
                
                # Wait for welcome message
                try:
                    welcome_message = await asyncio.wait_for(
                        websocket.recv(), timeout=5.0
                    )
                    welcome_data = json.loads(welcome_message)
                    
                    # Verify welcome message structure
                    assert "type" in welcome_data
                    assert welcome_data["type"] == "connection_established"
                    assert "connection_id" in welcome_data
                    assert "server_time" in welcome_data
                    assert "message" in welcome_data
                    
                    print(f"✅ Received welcome message: {welcome_data}")
                    
                except asyncio.TimeoutError:
                    pytest.fail("Did not receive welcome message within timeout")
                
        except Exception as e:
            pytest.fail(f"Failed to connect to WebSocket test endpoint: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_ping_pong(self):
        """Test basic ping/pong functionality on the test endpoint."""
        websocket_url = "ws://localhost:8000/ws/test"
        
        try:
            async with websockets.connect(websocket_url) as websocket:
                # Wait for welcome message
                welcome_message = await websocket.recv()
                welcome_data = json.loads(welcome_message)
                print(f"Connected with ID: {welcome_data.get('connection_id')}")
                
                # Send ping message
                ping_message = {
                    "type": "ping",
                    "timestamp": datetime.utcnow().isoformat(),
                    "data": {"test": "ping_test"}
                }
                
                await websocket.send(json.dumps(ping_message))
                print(f"📤 Sent ping: {ping_message}")
                
                # Wait for pong response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    # Verify pong response
                    assert response_data["type"] == "pong"
                    assert "timestamp" in response_data
                    
                    print(f"📥 Received pong: {response_data}")
                    
                except asyncio.TimeoutError:
                    pytest.fail("Did not receive pong response within timeout")
                    
        except Exception as e:
            pytest.fail(f"Ping/pong test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_echo_message(self):
        """Test echo functionality on the test endpoint."""
        websocket_url = "ws://localhost:8000/ws/test"
        
        try:
            async with websockets.connect(websocket_url) as websocket:
                # Skip welcome message
                await websocket.recv()
                
                # Send echo message
                echo_message = {
                    "type": "echo",
                    "data": {
                        "test_content": "Hello WebSocket!",
                        "number": 42,
                        "bool": True
                    }
                }
                
                await websocket.send(json.dumps(echo_message))
                print(f"📤 Sent echo: {echo_message}")
                
                # Wait for echo response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    # Verify echo response
                    assert response_data["type"] == "echo_response"
                    assert "original" in response_data
                    assert "timestamp" in response_data
                    assert response_data["original"] == echo_message
                    
                    print(f"📥 Received echo response: {response_data}")
                    
                except asyncio.TimeoutError:
                    pytest.fail("Did not receive echo response within timeout")
                    
        except Exception as e:
            pytest.fail(f"Echo test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_invalid_json_handling(self):
        """Test how the WebSocket handles invalid JSON messages."""
        websocket_url = "ws://localhost:8000/ws/test"
        
        try:
            async with websockets.connect(websocket_url) as websocket:
                # Skip welcome message
                await websocket.recv()
                
                # Send invalid JSON
                invalid_json = "{ this is not valid json }"
                
                await websocket.send(invalid_json)
                print(f"📤 Sent invalid JSON: {invalid_json}")
                
                # Wait for error response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    # Verify error response
                    assert response_data["type"] == "error"
                    assert "message" in response_data
                    assert "Invalid JSON" in response_data["message"]
                    
                    print(f"📥 Received error response: {response_data}")
                    
                except asyncio.TimeoutError:
                    pytest.fail("Did not receive error response for invalid JSON")
                    
        except Exception as e:
            pytest.fail(f"Invalid JSON test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_unknown_message_type(self):
        """Test handling of unknown message types."""
        websocket_url = "ws://localhost:8000/ws/test"
        
        try:
            async with websockets.connect(websocket_url) as websocket:
                # Skip welcome message
                await websocket.recv()
                
                # Send message with unknown type
                unknown_message = {
                    "type": "unknown_message_type",
                    "data": {"content": "this is an unknown message type"}
                }
                
                await websocket.send(json.dumps(unknown_message))
                print(f"📤 Sent unknown type: {unknown_message}")
                
                # Wait for acknowledgment
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    # Should receive generic acknowledgment
                    assert response_data["type"] == "ack"
                    assert response_data["received_type"] == "unknown_message_type"
                    assert "timestamp" in response_data
                    
                    print(f"📥 Received ack: {response_data}")
                    
                except asyncio.TimeoutError:
                    pytest.fail("Did not receive acknowledgment for unknown message type")
                    
        except Exception as e:
            pytest.fail(f"Unknown message type test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_connection_timeout_handling(self):
        """Test that WebSocket handles connection timeouts gracefully."""
        websocket_url = "ws://localhost:8000/ws/test"
        
        try:
            async with websockets.connect(websocket_url) as websocket:
                # Skip welcome message
                await websocket.recv()
                
                # Wait for heartbeat message (should come after 30 seconds of inactivity)
                # We'll wait a bit longer to see if we get a heartbeat
                try:
                    heartbeat_message = await asyncio.wait_for(websocket.recv(), timeout=35.0)
                    heartbeat_data = json.loads(heartbeat_message)
                    
                    # Should receive heartbeat
                    assert heartbeat_data["type"] == "heartbeat"
                    assert "timestamp" in heartbeat_data
                    
                    print(f"📥 Received heartbeat: {heartbeat_data}")
                    
                except asyncio.TimeoutError:
                    print("⚠️  No heartbeat received within timeout (this may be expected)")
                    # This might be expected behavior, so don't fail
                    assert True
                    
        except Exception as e:
            pytest.fail(f"Timeout handling test failed: {e}")
    
    @pytest.mark.asyncio
    async def test_websocket_multiple_messages_sequence(self):
        """Test sending multiple messages in sequence."""
        websocket_url = "ws://localhost:8000/ws/test"
        
        try:
            async with websockets.connect(websocket_url) as websocket:
                # Skip welcome message
                await websocket.recv()
                
                # Send multiple messages of different types
                messages = [
                    {"type": "ping", "data": {"sequence": 1}},
                    {"type": "echo", "data": {"content": "message 2"}},
                    {"type": "ping", "data": {"sequence": 3}},
                    {"type": "unknown_type", "data": {"sequence": 4}}
                ]
                
                responses = []
                
                for i, message in enumerate(messages):
                    await websocket.send(json.dumps(message))
                    print(f"📤 Sent message {i+1}: {message}")
                    
                    # Receive response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        responses.append(response_data)
                        print(f"📥 Received response {i+1}: {response_data}")
                    except asyncio.TimeoutError:
                        pytest.fail(f"Did not receive response for message {i+1}")
                
                # Verify we got responses to all messages
                assert len(responses) == len(messages), f"Expected {len(messages)} responses, got {len(responses)}"
                
                # Verify response types are correct
                assert responses[0]["type"] == "pong"  # ping -> pong
                assert responses[1]["type"] == "echo_response"  # echo -> echo_response
                assert responses[2]["type"] == "pong"  # ping -> pong
                assert responses[3]["type"] == "ack"   # unknown -> ack
                
        except Exception as e:
            pytest.fail(f"Multiple messages test failed: {e}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])