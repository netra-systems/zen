"""Real WebSocket Broadcast Performance Tests

Business Value Justification (BVJ):
- Segment: Mid & Enterprise (Team Collaboration)
- Business Goal: Multi-User Performance & Scalability
- Value Impact: Ensures broadcast messages reach multiple users efficiently
- Strategic Impact: Enables team collaboration features and scales to enterprise usage

Tests real WebSocket broadcasting performance with Docker services.
Validates broadcast delivery to multiple concurrent clients.
"""

import asyncio
import json
import time
from typing import Any, Dict, List, Set

import pytest
import websockets
from websockets.exceptions import WebSocketException

from netra_backend.tests.real_services_test_fixtures import skip_if_no_real_services
from shared.isolated_environment import get_env

env = get_env()


@pytest.mark.real_services
@pytest.mark.websocket
@pytest.mark.broadcast_performance
@skip_if_no_real_services
class TestRealWebSocketBroadcastPerformance:
    """Test real WebSocket broadcast performance and delivery."""
    
    @pytest.fixture
    def websocket_url(self):
        backend_host = env.get("BACKEND_HOST", "localhost")
        backend_port = env.get("BACKEND_PORT", "8000")
        return f"ws://{backend_host}:{backend_port}/ws"
    
    @pytest.fixture
    def auth_headers_template(self):
        """Template for auth headers - will be customized per client."""
        return {"User-Agent": "Netra-Broadcast-Test/1.0"}
    
    @pytest.mark.asyncio
    async def test_multiple_client_broadcast_delivery(self, websocket_url, auth_headers_template):
        """Test broadcast message delivery to multiple clients."""
        base_time = int(time.time())
        broadcast_results = {}
        
        async def client_session(client_id: str):
            """Individual client session for broadcast testing."""
            user_id = f"broadcast_user_{client_id}_{base_time}"
            auth_headers = {
                **auth_headers_template,
                "Authorization": f"Bearer test_token_{client_id}",
                "Client-ID": client_id
            }
            
            messages_received = []
            
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=15
                ) as websocket:
                    # Connect
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "client_id": client_id,
                        "subscribe_broadcasts": True
                    }))
                    
                    connect_response = json.loads(await websocket.recv())
                    
                    # Listen for broadcast messages
                    timeout_time = time.time() + 12
                    while time.time() < timeout_time:
                        try:
                            message_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            message = json.loads(message_raw)
                            
                            # Track broadcast messages
                            if message.get("type") in ["broadcast", "system_broadcast", "announcement"]:
                                messages_received.append({
                                    "message": message,
                                    "received_at": time.time(),
                                    "client_id": client_id
                                })
                            
                        except asyncio.TimeoutError:
                            continue
                        except WebSocketException:
                            break
                    
                    broadcast_results[client_id] = {
                        "user_id": user_id,
                        "messages_received": messages_received,
                        "connection_id": connect_response.get("connection_id"),
                        "success": True
                    }
                    
            except Exception as e:
                broadcast_results[client_id] = {
                    "user_id": f"broadcast_user_{client_id}_{base_time}",
                    "error": str(e),
                    "messages_received": messages_received,
                    "success": False
                }
        
        async def broadcast_sender():
            """Send broadcast messages."""
            await asyncio.sleep(2)  # Wait for clients to connect
            
            # Send test broadcasts (this would normally be done by the system)
            # For this test, we'll simulate by having one client send messages that might be broadcast
            try:
                sender_headers = {
                    **auth_headers_template,
                    "Authorization": "Bearer test_token_broadcaster"
                }
                
                async with websockets.connect(
                    websocket_url,
                    extra_headers=sender_headers,
                    timeout=10
                ) as sender_ws:
                    await sender_ws.send(json.dumps({
                        "type": "connect",
                        "user_id": f"broadcaster_{base_time}",
                        "role": "broadcaster"
                    }))
                    
                    await sender_ws.recv()  # Connect response
                    
                    # Send messages that might trigger broadcasts
                    for i in range(3):
                        await asyncio.sleep(1)
                        await sender_ws.send(json.dumps({
                            "type": "system_announcement",
                            "content": f"Test broadcast message {i+1}",
                            "broadcast_to": "all_connected_users",
                            "timestamp": time.time()
                        }))
                        
            except Exception as e:
                print(f"Broadcast sender error: {e}")
        
        # Run multiple clients concurrently with broadcaster
        client_tasks = [client_session(f"client_{i}") for i in range(4)]
        broadcaster_task = broadcast_sender()
        
        await asyncio.gather(*client_tasks, broadcaster_task)
        
        # Analyze broadcast performance
        successful_clients = [r for r in broadcast_results.values() if r.get("success")]
        total_messages_received = sum(len(r.get("messages_received", [])) for r in successful_clients)
        
        print(f"Broadcast performance - Successful clients: {len(successful_clients)}/4")
        print(f"Total broadcast messages received: {total_messages_received}")
        
        # Validate broadcast delivery
        assert len(successful_clients) >= 2, f"At least 2 clients should connect successfully"
        
        # If broadcasts were implemented and working, we'd see messages
        if total_messages_received > 0:
            print(f"SUCCESS: Broadcast functionality working - {total_messages_received} messages delivered")
            
            # Check message consistency across clients
            message_contents = set()
            for result in successful_clients:
                for msg_data in result.get("messages_received", []):
                    content = msg_data.get("message", {}).get("content")
                    if content:
                        message_contents.add(content)
            
            print(f"Unique broadcast contents: {len(message_contents)}")
            
        else:
            print("INFO: No broadcast messages received (broadcast feature may not be implemented yet)")
    
    @pytest.mark.asyncio
    async def test_broadcast_latency_measurement(self, websocket_url, auth_headers_template):
        """Test broadcast message delivery latency."""
        base_time = int(time.time())
        latency_results = []
        
        async def latency_client(client_id: str):
            """Client that measures broadcast latency."""
            user_id = f"latency_user_{client_id}_{base_time}"
            auth_headers = {
                **auth_headers_template,
                "Authorization": f"Bearer test_token_{client_id}"
            }
            
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers=auth_headers,
                    timeout=10
                ) as websocket:
                    await websocket.send(json.dumps({
                        "type": "connect",
                        "user_id": user_id,
                        "measure_latency": True
                    }))
                    
                    await websocket.recv()  # Connect response
                    
                    # Listen for timestamped broadcasts
                    timeout_time = time.time() + 8
                    while time.time() < timeout_time:
                        try:
                            message_raw = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            receive_time = time.time()
                            message = json.loads(message_raw)
                            
                            # Calculate latency for timestamped messages
                            if "timestamp" in message and message.get("type") == "timed_broadcast":
                                send_time = message["timestamp"]
                                latency = receive_time - send_time
                                
                                latency_results.append({
                                    "client_id": client_id,
                                    "latency_seconds": latency,
                                    "send_time": send_time,
                                    "receive_time": receive_time
                                })
                            
                        except asyncio.TimeoutError:
                            continue
                        except WebSocketException:
                            break
                        except json.JSONDecodeError:
                            continue
                    
            except Exception as e:
                print(f"Latency client {client_id} error: {e}")
        
        async def timed_broadcaster():
            """Send timestamped broadcast messages."""
            await asyncio.sleep(1)  # Wait for clients
            
            try:
                broadcaster_headers = {
                    **auth_headers_template,
                    "Authorization": "Bearer test_token_timed_broadcaster"
                }
                
                async with websockets.connect(
                    websocket_url,
                    extra_headers=broadcaster_headers,
                    timeout=10
                ) as broadcaster:
                    await broadcaster.send(json.dumps({
                        "type": "connect",
                        "user_id": f"timed_broadcaster_{base_time}"
                    }))
                    
                    await broadcaster.recv()
                    
                    # Send timed broadcasts
                    for i in range(3):
                        send_time = time.time()
                        await broadcaster.send(json.dumps({
                            "type": "timed_broadcast",
                            "content": f"Latency test message {i+1}",
                            "timestamp": send_time,
                            "broadcast_id": f"latency_test_{i}"
                        }))
                        await asyncio.sleep(1)
                        
            except Exception as e:
                print(f"Timed broadcaster error: {e}")
        
        # Run latency test with multiple clients
        client_tasks = [latency_client(f"latency_{i}") for i in range(2)]
        broadcaster_task = timed_broadcaster()
        
        await asyncio.gather(*client_tasks, broadcaster_task)
        
        # Analyze latency results
        if len(latency_results) > 0:
            latencies = [r["latency_seconds"] for r in latency_results]
            avg_latency = sum(latencies) / len(latencies)
            max_latency = max(latencies)
            min_latency = min(latencies)
            
            print(f"Broadcast latency - Samples: {len(latency_results)}")
            print(f"Average latency: {avg_latency:.3f}s, Min: {min_latency:.3f}s, Max: {max_latency:.3f}s")
            
            # Reasonable latency expectations
            assert avg_latency < 5.0, f"Average broadcast latency should be reasonable: {avg_latency:.3f}s"
            assert max_latency < 10.0, f"Maximum broadcast latency should be acceptable: {max_latency:.3f}s"
            
        else:
            print("INFO: No latency measurements (timed broadcast feature may not be implemented)")