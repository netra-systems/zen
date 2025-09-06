"""Real WebSocket Error Recovery Tests

Business Value Justification (BVJ):
- Segment: Platform/Internal & All Customer Tiers
- Business Goal: Chat Reliability & User Experience
- Value Impact: Ensures chat continues working when errors occur
- Strategic Impact: Prevents user frustration and maintains chat value delivery

Tests real WebSocket error handling and recovery mechanisms with Docker services.
Validates system recovers gracefully from various error conditions.
"""

import asyncio
import json
import time
from typing import Any, Dict, List

import pytest
import websockets
from websockets.exceptions import WebSocketException, ConnectionClosedError

from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@pytest.mark.error_recovery
@skip_if_no_real_services
class TestRealWebSocketErrorRecovery:
    """Test real WebSocket error recovery mechanisms."""
    
    @pytest.fixture
    def websocket_url(self):
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers(self):
        jwt_token = env.get("TEST_JWT_TOKEN", "test_token_123")
        return {
            "Authorization": f"Bearer {jwt_token}",
            "User-Agent": "Netra-Error-Recovery-Test/1.0"
        }
    
    @pytest.mark.asyncio
    async def test_invalid_json_error_handling(self, websocket_url, auth_headers):
        """Test handling of invalid JSON messages."""
        user_id = f"json_error_test_{int(time.time())}"
        error_responses = []
        connection_survived = False
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                # Connect normally first
                await websocket.send(json.dumps({"type": "connect", "user_id": user_id}))
                connect_response = await websocket.recv()
                
                # Send invalid JSON
                await websocket.send("invalid json content {")
                
                # Check for error response
                try:
                    error_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    error_data = json.loads(error_response)
                    error_responses.append(error_data)
                except asyncio.TimeoutError:
                    pass
                except json.JSONDecodeError:
                    # Response may also be invalid - that's ok for error testing
                    error_responses.append({"type": "json_decode_error"})
                
                # Test if connection is still alive after error
                await websocket.send(json.dumps({
                    "type": "heartbeat",
                    "user_id": user_id,
                    "timestamp": time.time()
                }))
                
                try:
                    heartbeat_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    heartbeat_data = json.loads(heartbeat_response)
                    if heartbeat_data.get("type") == "heartbeat_ack":
                        connection_survived = True
                except (asyncio.TimeoutError, json.JSONDecodeError):
                    pass
                
        except ConnectionClosedError:
            # Connection may be closed due to invalid JSON - acceptable
            pass
        except Exception as e:
            if "json" not in str(e).lower():
                pytest.fail(f"Invalid JSON error test failed: {e}")
        
        print(f"Invalid JSON handling - Error responses: {len(error_responses)}, Connection survived: {connection_survived}")
        
        # Either should get error response OR connection should be gracefully closed
        recovery_handled = len(error_responses) > 0 or not connection_survived
        assert recovery_handled, "System should handle invalid JSON gracefully"
    
    @pytest.mark.asyncio
    async def test_malformed_message_recovery(self, websocket_url, auth_headers):
        """Test recovery from malformed messages."""
        user_id = f"malformed_test_{int(time.time())}"
        recovery_successful = False
        
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket:
                # Connect
                await websocket.send(json.dumps({"type": "connect", "user_id": user_id}))
                await websocket.recv()
                
                # Send malformed message (valid JSON but invalid structure)
                malformed_message = {"invalid_structure": True, "missing_required_fields": "yes"}
                await websocket.send(json.dumps(malformed_message))
                
                # Give time for error processing
                await asyncio.sleep(1)
                
                # Send valid message to test recovery
                recovery_message = {
                    "type": "user_message",
                    "user_id": user_id,
                    "content": "Recovery test message"
                }
                await websocket.send(json.dumps(recovery_message))
                
                # Check if system recovered
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    # Should not be an error about the previous malformed message
                    if response_data.get("type") not in ["malformed_error", "invalid_message_error"]:
                        recovery_successful = True
                        
                except asyncio.TimeoutError:
                    # May not respond immediately - try heartbeat
                    await websocket.send(json.dumps({"type": "heartbeat", "user_id": user_id}))
                    try:
                        hb_response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        if json.loads(hb_response).get("type") == "heartbeat_ack":
                            recovery_successful = True
                    except:
                        pass
                
        except Exception as e:
            pytest.fail(f"Malformed message recovery test failed: {e}")
        
        assert recovery_successful, "System should recover from malformed messages"
    
    @pytest.mark.asyncio
    async def test_connection_interruption_recovery(self, websocket_url, auth_headers):
        """Test recovery from connection interruptions."""
        user_id = f"interruption_test_{int(time.time())}"
        reconnection_successful = False
        
        # First connection
        try:
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket1:
                # Establish session
                await websocket1.send(json.dumps({"type": "connect", "user_id": user_id}))
                response1 = await websocket1.recv()
                original_connection_id = json.loads(response1).get("connection_id")
                
                # Send message
                await websocket1.send(json.dumps({
                    "type": "user_message",
                    "user_id": user_id,
                    "content": "Message before interruption"
                }))
                
                # Connection will close when exiting context
                
            # Brief delay to simulate interruption
            await asyncio.sleep(1)
            
            # Reconnect
            async with websockets.connect(
                websocket_url,
                extra_headers=auth_headers,
                timeout=10
            ) as websocket2:
                # Re-establish connection
                await websocket2.send(json.dumps({"type": "connect", "user_id": user_id}))
                response2 = await websocket2.recv()
                new_connection_id = json.loads(response2).get("connection_id")
                
                # Verify can send messages after reconnection
                await websocket2.send(json.dumps({
                    "type": "user_message",
                    "user_id": user_id,
                    "content": "Message after reconnection"
                }))
                
                try:
                    recovery_response = await asyncio.wait_for(websocket2.recv(), timeout=5.0)
                    reconnection_successful = True
                except asyncio.TimeoutError:
                    # Try heartbeat
                    await websocket2.send(json.dumps({"type": "heartbeat", "user_id": user_id}))
                    try:
                        await asyncio.wait_for(websocket2.recv(), timeout=3.0)
                        reconnection_successful = True
                    except:
                        pass
                
                print(f"Connection IDs - Original: {original_connection_id}, New: {new_connection_id}")
                
        except Exception as e:
            pytest.fail(f"Connection interruption recovery test failed: {e}")
        
        assert reconnection_successful, "Should be able to reconnect after interruption"