"""
WebSocket Development Connectivity Test
Tests WebSocket connectivity for dev launcher environment validation.

Business Value Justification (BVJ):
- Segment: Platform/Internal - Development Environment
- Business Goal: Development Velocity & System Stability
- Value Impact: Ensures WebSocket connectivity works in dev environment
- Strategic Impact: Prevents dev environment broken states, reduces developer friction
"""

import asyncio
import json
import pytest
import websockets
from datetime import datetime
from typing import Dict, Any, Optional
import time
import uuid
from shared.isolated_environment import IsolatedEnvironment


@pytest.mark.e2e
class TestWebSocketDevConnectivity:
    """Test suite for WebSocket connectivity in development environment."""

    @pytest.mark.websocket
    async def test_dev_websocket_basic_connectivity(self):
        """
        Test basic WebSocket connectivity to the test endpoint.
        
        Critical Assertions:
        - WebSocket test endpoint accepts connections
        - Basic handshake works
        - Connection remains stable for message exchange
        - Proper cleanup on disconnect
        
        Expected Failure: WebSocket server not started
        Business Impact: No real-time features in dev environment
        """
        ws_url = "ws://localhost:8001/ws/test"
        
        try:
            # Test connection establishment
            async with websockets.connect(
                ws_url,
                ping_interval=None,  # Disable auto-ping for test control
                ping_timeout=10,
                close_timeout=5
            ) as websocket:
                # Verify connection is established (connection successful if we reach here)
                
                # Wait for welcome message
                welcome_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                welcome_data = json.loads(welcome_response)
                
                # Validate welcome message structure
                assert welcome_data.get("type") == "connection_established", \
                    f"Invalid welcome message: {welcome_data}"
                assert welcome_data.get("connection_id"), \
                    "No connection ID in welcome message"
                assert welcome_data.get("server_time"), \
                    "No server time in welcome message"
                
                connection_id = welcome_data["connection_id"]
                print(f"WebSocket connected with ID: {connection_id}")
                
        except asyncio.TimeoutError:
            raise AssertionError("WebSocket connection timeout - server not responding")
        except websockets.exceptions.WebSocketException as e:
            raise AssertionError(f"WebSocket connection failed: {str(e)}")
        except Exception as e:
            raise AssertionError(f"Unexpected WebSocket error: {str(e)}")

    @pytest.mark.websocket
    async def test_dev_websocket_message_echo(self):
        """
        Test WebSocket message echo functionality.
        
        Critical Assertions:
        - Can send messages to WebSocket server
        - Server responds with echo
        - Message content preserved
        - Timestamps included for latency measurement
        
        Expected Failure: Message handling not implemented
        Business Impact: Real-time messaging broken
        """
        ws_url = "ws://localhost:8001/ws/test"
        
        async with websockets.connect(ws_url) as websocket:
            # Skip welcome message
            await websocket.recv()
            
            # Test echo functionality
            test_payload = {
                "message": "Hello WebSocket",
                "timestamp": time.time(),
                "test_id": str(uuid.uuid4())
            }
            
            echo_request = {
                "type": "echo",
                "payload": test_payload
            }
            
            # Send echo request
            await websocket.send(json.dumps(echo_request))
            
            # Receive echo response
            echo_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            response_data = json.loads(echo_response)
            
            # Validate echo response
            assert response_data.get("type") == "echo_response", \
                f"Wrong response type: {response_data.get('type')}"
            assert response_data.get("original"), \
                "No original message in echo response"
            
            # Verify content preservation
            original = response_data["original"]
            assert original.get("payload") == test_payload, \
                "Echo payload mismatch"
            
            # Verify server timestamp added
            assert response_data.get("timestamp"), \
                "No server timestamp in echo response"
            
            print(f"Echo test passed - payload preserved, server timestamp added")

    @pytest.mark.websocket
    async def test_dev_websocket_ping_pong(self):
        """
        Test WebSocket ping/pong heartbeat functionality.
        
        Critical Assertions:
        - Server responds to ping messages
        - Pong includes server timestamp
        - Round-trip time measurable
        - Connection health maintained
        
        Expected Failure: Heartbeat mechanism not working
        Business Impact: Connections may drop unexpectedly
        """
        ws_url = "ws://localhost:8001/ws/test"
        
        async with websockets.connect(ws_url) as websocket:
            # Skip welcome message
            await websocket.recv()
            
            # Send ping message
            ping_time = time.time()
            ping_message = {
                "type": "ping",
                "client_timestamp": ping_time
            }
            
            await websocket.send(json.dumps(ping_message))
            
            # Receive pong response
            pong_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            pong_time = time.time()
            pong_data = json.loads(pong_response)
            
            # Validate pong response
            assert pong_data.get("type") == "pong", \
                f"Wrong response type: {pong_data.get('type')}"
            assert pong_data.get("timestamp"), \
                "No server timestamp in pong"
            
            # Calculate round-trip time
            round_trip_time = pong_time - ping_time
            assert round_trip_time < 1.0, \
                f"Round-trip time too high: {round_trip_time}s"
            
            print(f"Ping/pong successful - RTT: {round_trip_time:.3f}s")

    @pytest.mark.websocket
    async def test_dev_websocket_error_handling(self):
        """
        Test WebSocket error handling for malformed messages.
        
        Critical Assertions:
        - Server handles invalid JSON gracefully
        - Error messages returned with proper format
        - Connection remains stable after errors
        - Error codes provided for debugging
        
        Expected Failure: Error handling not implemented
        Business Impact: Poor dev experience, hard to debug issues
        """
        ws_url = "ws://localhost:8001/ws/test"
        
        async with websockets.connect(ws_url) as websocket:
            # Skip welcome message
            await websocket.recv()
            
            # Send invalid JSON
            await websocket.send("invalid json {")
            
            # Should receive error message
            error_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            error_data = json.loads(error_response)
            
            assert error_data.get("type") == "error", \
                f"Expected error message, got: {error_data.get('type')}"
            assert "Invalid JSON" in error_data.get("message", ""), \
                f"Error message doesn't mention JSON: {error_data.get('message')}"
            
            # Verify connection is still active by sending valid message
            test_message = {
                "type": "echo",
                "payload": "Connection still active"
            }
            
            await websocket.send(json.dumps(test_message))
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            response_data = json.loads(response)
            
            assert response_data.get("type") == "echo_response", \
                "Connection not stable after error"
            
            print("Error handling works - connection stable after invalid JSON")

    @pytest.mark.websocket
    async def test_dev_websocket_multiple_messages(self):
        """
        Test WebSocket handling of multiple rapid messages.
        
        Critical Assertions:
        - Can send multiple messages rapidly
        - All messages processed in order
        - No message loss
        - Performance acceptable for dev environment
        
        Expected Failure: Message queue overflow or ordering issues
        Business Impact: Unreliable real-time communication
        """
        ws_url = "ws://localhost:8001/ws/test"
        
        async with websockets.connect(ws_url) as websocket:
            # Skip welcome message
            await websocket.recv()
            
            # Send multiple messages rapidly
            message_count = 5
            sent_messages = []
            
            for i in range(message_count):
                message = {
                    "type": "echo",
                    "payload": f"Message {i}",
                    "sequence": i
                }
                sent_messages.append(message)
                await websocket.send(json.dumps(message))
            
            # Receive all responses
            received_responses = []
            for i in range(message_count):
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                received_responses.append(response_data)
            
            # Verify all messages processed
            assert len(received_responses) == message_count, \
                f"Message count mismatch: sent {message_count}, received {len(received_responses)}"
            
            # Verify message order preservation
            for i, response in enumerate(received_responses):
                assert response.get("type") == "echo_response", \
                    f"Wrong response type for message {i}"
                original = response.get("original", {})
                assert original.get("sequence") == i, \
                    f"Message order not preserved: expected {i}, got {original.get('sequence')}"
                assert original.get("payload") == f"Message {i}", \
                    f"Message content not preserved for message {i}"
            
            print(f"Multiple messages handled correctly - {message_count} messages processed in order")

    @pytest.mark.websocket
    async def test_dev_websocket_connection_info(self):
        """
        Test WebSocket provides useful connection information for debugging.
        
        Critical Assertions:
        - Welcome message contains connection details
        - Server time provided for sync
        - Connection ID unique per connection
        - Message format suitable for debugging
        
        Expected Failure: Missing debug information
        Business Impact: Harder to debug WebSocket issues in development
        """
        ws_url = "ws://localhost:8001/ws/test"
        
        # Test multiple connections get unique IDs
        connection_ids = set()
        
        for connection_num in range(2):
            async with websockets.connect(ws_url) as websocket:
                welcome_response = await asyncio.wait_for(websocket.recv(), timeout=5)
                welcome_data = json.loads(welcome_response)
                
                connection_id = welcome_data.get("connection_id")
                assert connection_id, f"No connection ID for connection {connection_num}"
                assert connection_id not in connection_ids, \
                    f"Duplicate connection ID: {connection_id}"
                
                connection_ids.add(connection_id)
                
                # Verify server time format
                server_time = welcome_data.get("server_time")
                assert server_time, "No server time provided"
                
                # Try to parse ISO format timestamp
                try:
                    datetime.fromisoformat(server_time.replace('Z', '+00:00'))
                except ValueError:
                    raise AssertionError(f"Invalid server time format: {server_time}")
                
                # Verify message format useful for debugging
                assert welcome_data.get("message"), "No welcome message provided"
                
        print(f"Connection info validated - {len(connection_ids)} unique connections")

    @pytest.mark.asyncio
    async def test_websocket_availability_check(self):
        """
        Quick availability check for WebSocket service.
        This test ensures the WebSocket service is running and responding.
        
        Critical for: Dev launcher readiness checks
        """
        ws_url = "ws://localhost:8001/ws/test"
        
        try:
            # Use asyncio.timeout for Python 3.12 compatibility
            async with asyncio.timeout(3):  # 3 second timeout for connection
                async with websockets.connect(
                    ws_url,
                    close_timeout=1
                ) as websocket:
                    # Just verify connection works
                    welcome = await asyncio.wait_for(websocket.recv(), timeout=2)
                    welcome_data = json.loads(welcome)
                
                assert welcome_data.get("type") == "connection_established", \
                    "WebSocket not ready"
                
                print("WebSocket service available and responding")
                
        except Exception as e:
            raise AssertionError(f"WebSocket service not available: {str(e)}")


if __name__ == "__main__":
    # Allow running the test directly for quick validation
    async def run_quick_test():
        test_instance = TestWebSocketDevConnectivity()
        try:
            await test_instance.test_websocket_availability_check()
            print("Quick WebSocket connectivity test passed")
        except Exception as e:
            print(f"FAILED Quick WebSocket connectivity test failed: {e}")
            return False
        return True
    
    if asyncio.run(run_quick_test()):
        print("SUCCESS WebSocket connectivity validation successful")
    else:
        print("FAILED WebSocket connectivity validation failed")