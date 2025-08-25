"""
E2E Test: WebSocket Real-time Features

This test validates that WebSocket connections work correctly for real-time features
including agent communication, live updates, and message broadcasting.

Business Value Justification (BVJ):
- Segment: Early, Mid, Enterprise (real-time features are premium)
- Business Goal: Real-time user engagement and premium feature differentiation
- Value Impact: Enables live collaboration and instant AI agent responses
- Strategic/Revenue Impact: Real-time features drive Premium/Enterprise tier conversion
"""

import asyncio
import aiohttp
import json
import pytest
import websockets
import time
import uuid
from typing import Dict, Any, List, Optional
from concurrent.futures import ThreadPoolExecutor

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_websocket_connection_establishment():
    """Test that WebSocket connections can be established with proper authentication.
    
    This test should FAIL until WebSocket infrastructure is properly implemented.
    """
    
    websocket_url = "ws://localhost:8000/websocket"
    auth_service_url = "http://localhost:8001"
    
    connection_failures = []
    
    # Step 1: Get authentication token
    auth_token = None
    async with aiohttp.ClientSession() as session:
        print("🔐 Getting authentication token for WebSocket connection...")
        try:
            # Try to get a test token
            login_data = {
                "email": "test@example.com", 
                "password": "testpassword"
            }
            async with session.post(f"{auth_service_url}/login", json=login_data) as response:
                if response.status == 200:
                    result = await response.json()
                    auth_token = result.get("access_token")
                    print(f"✅ Authentication token obtained")
                else:
                    connection_failures.append("Failed to obtain auth token for WebSocket test")
        except Exception as e:
            connection_failures.append(f"Auth token request failed: {e}")
    
    # Step 2: Test WebSocket Connection
    print("🔌 Testing WebSocket connection establishment...")
    
    try:
        # Attempt WebSocket connection with authentication
        headers = {}
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        
        # Fix WebSocket connection parameters
        connection_args = {
            "ping_timeout": 10,
        }
        if headers:
            connection_args["additional_headers"] = headers
            
        async with websockets.connect(
            websocket_url,
            **connection_args
        ) as websocket:
            print("✅ WebSocket connection established successfully")
            
            # Test basic ping/pong
            await websocket.ping()
            print("✅ WebSocket ping/pong working")
            
            # Test message sending
            test_message = {
                "type": "ping",
                "timestamp": time.time(),
                "client_id": str(uuid.uuid4())
            }
            
            await websocket.send(json.dumps(test_message))
            print("✅ WebSocket message sent")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                print(f"✅ WebSocket response received: {response_data.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                connection_failures.append("WebSocket response timeout")
            
    except ConnectionRefusedError:
        connection_failures.append("WebSocket connection refused - server not running")
    except websockets.exceptions.InvalidURI:
        connection_failures.append("Invalid WebSocket URI")
    except Exception as e:
        connection_failures.append(f"WebSocket connection failed: {e}")
    
    if connection_failures:
        failure_report = ["🔌 WebSocket Connection Failures:"]
        for failure in connection_failures:
            failure_report.append(f"  - {failure}")
        
        pytest.fail(f"WebSocket connection test failed:\n" + "\n".join(failure_report))
    
    print("✅ WebSocket connection test passed")


@pytest.mark.e2e
@pytest.mark.asyncio
async def test_agent_communication_websocket():
    """Test real-time AI agent communication over WebSocket.
    
    This test should FAIL until agent communication infrastructure is implemented.
    """
    
    websocket_url = "ws://localhost:8000/websocket"
    agent_communication_failures = []
    
    print("🤖 Testing AI agent communication over WebSocket...")
    
    try:
        async with websockets.connect(websocket_url, ping_timeout=10) as websocket:
            
            # Test 1: Agent Task Creation
            agent_task = {
                "type": "agent_task",
                "task_id": str(uuid.uuid4()),
                "agent_type": "supervisor_agent",
                "task_data": {
                    "prompt": "Hello, this is a test task",
                    "priority": "normal",
                    "user_id": "test_user_123"
                },
                "timestamp": time.time()
            }
            
            await websocket.send(json.dumps(agent_task))
            print("✅ Agent task sent via WebSocket")
            
            # Wait for agent acknowledgment
            try:
                ack_response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                ack_data = json.loads(ack_response)
                
                if ack_data.get("type") != "agent_task_ack":
                    agent_communication_failures.append(f"Expected agent_task_ack, got {ack_data.get('type')}")
                elif ack_data.get("task_id") != agent_task["task_id"]:
                    agent_communication_failures.append("Agent task acknowledgment has mismatched task_id")
                else:
                    print("✅ Agent task acknowledged")
                    
            except asyncio.TimeoutError:
                agent_communication_failures.append("Agent task acknowledgment timeout")
            
            # Test 2: Agent Response Streaming
            print("📡 Testing agent response streaming...")
            
            # Wait for agent response chunks
            response_chunks = []
            start_time = time.time()
            
            while time.time() - start_time < 15.0:  # 15 second timeout
                try:
                    chunk = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    chunk_data = json.loads(chunk)
                    
                    if chunk_data.get("task_id") == agent_task["task_id"]:
                        response_chunks.append(chunk_data)
                        
                        if chunk_data.get("type") == "agent_response_complete":
                            print(f"✅ Agent response completed ({len(response_chunks)} chunks)")
                            break
                        elif chunk_data.get("type") == "agent_response_chunk":
                            print(f"📄 Agent response chunk received")
                            
                except asyncio.TimeoutError:
                    break
            
            if not response_chunks:
                agent_communication_failures.append("No agent response chunks received")
            elif not any(chunk.get("type") == "agent_response_complete" for chunk in response_chunks):
                agent_communication_failures.append("Agent response never completed")
            
            # Test 3: Agent Status Updates
            print("📊 Testing agent status updates...")
            
            status_request = {
                "type": "agent_status_request",
                "request_id": str(uuid.uuid4()),
                "timestamp": time.time()
            }
            
            await websocket.send(json.dumps(status_request))
            
            try:
                status_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                status_data = json.loads(status_response)
                
                if status_data.get("type") == "agent_status_update":
                    active_agents = status_data.get("active_agents", [])
                    print(f"✅ Agent status received: {len(active_agents)} active agents")
                else:
                    agent_communication_failures.append(f"Expected agent_status_update, got {status_data.get('type')}")
                    
            except asyncio.TimeoutError:
                agent_communication_failures.append("Agent status request timeout")
            
    except Exception as e:
        agent_communication_failures.append(f"Agent communication WebSocket failed: {e}")
    
    if agent_communication_failures:
        failure_report = ["🤖 Agent Communication Failures:"]
        for failure in agent_communication_failures:
            failure_report.append(f"  - {failure}")
        
        pytest.fail(f"Agent communication test failed:\n" + "\n".join(failure_report))
    
    print("✅ Agent communication test passed")


@pytest.mark.e2e 
@pytest.mark.asyncio
async def test_multi_client_websocket_broadcasting():
    """Test message broadcasting to multiple WebSocket clients.
    
    This test should FAIL until multi-client broadcasting is implemented.
    """
    
    websocket_url = "ws://localhost:8000/websocket"
    broadcasting_failures = []
    
    print("📡 Testing multi-client WebSocket broadcasting...")
    
    try:
        # Connect multiple WebSocket clients
        clients = []
        client_count = 3
        
        for i in range(client_count):
            try:
                client = await websockets.connect(
                    websocket_url,
                    ping_timeout=10,
                    close_timeout=10
                )
                clients.append({
                    "id": i,
                    "websocket": client,
                    "received_messages": []
                })
                print(f"✅ Client {i} connected")
            except Exception as e:
                broadcasting_failures.append(f"Failed to connect client {i}: {e}")
        
        if len(clients) < 2:
            broadcasting_failures.append("Insufficient clients connected for broadcast test")
        else:
            # Test broadcast message
            broadcast_message = {
                "type": "broadcast_test",
                "message": "Hello all clients!",
                "broadcast_id": str(uuid.uuid4()),
                "timestamp": time.time()
            }
            
            # Send broadcast message from first client
            await clients[0]["websocket"].send(json.dumps(broadcast_message))
            print("📢 Broadcast message sent from client 0")
            
            # Collect messages from all clients
            await asyncio.sleep(2)  # Give time for message propagation
            
            for i, client in enumerate(clients):
                try:
                    while True:
                        message = await asyncio.wait_for(
                            client["websocket"].recv(),
                            timeout=1.0
                        )
                        client["received_messages"].append(json.loads(message))
                except asyncio.TimeoutError:
                    pass  # No more messages
                except Exception as e:
                    broadcasting_failures.append(f"Error receiving messages on client {i}: {e}")
            
            # Verify broadcast received by other clients
            broadcast_received_count = 0
            for i, client in enumerate(clients[1:], 1):  # Skip sender
                broadcast_received = any(
                    msg.get("broadcast_id") == broadcast_message["broadcast_id"]
                    for msg in client["received_messages"]
                )
                if broadcast_received:
                    broadcast_received_count += 1
                    print(f"✅ Client {i} received broadcast message")
                else:
                    broadcasting_failures.append(f"Client {i} did not receive broadcast message")
            
            if broadcast_received_count == 0:
                broadcasting_failures.append("No clients received broadcast message")
            elif broadcast_received_count < len(clients) - 1:
                broadcasting_failures.append(f"Only {broadcast_received_count}/{len(clients)-1} clients received broadcast")
            
            # Test selective messaging
            print("🎯 Testing selective client messaging...")
            
            selective_message = {
                "type": "direct_message",
                "target_client": 1,
                "message": "This is for client 1 only",
                "message_id": str(uuid.uuid4()),
                "timestamp": time.time()
            }
            
            await clients[0]["websocket"].send(json.dumps(selective_message))
            await asyncio.sleep(1)
            
            # Check if only target client received the message
            target_received = False
            others_received = 0
            
            for i, client in enumerate(clients):
                try:
                    while True:
                        message = await asyncio.wait_for(
                            client["websocket"].recv(),
                            timeout=0.5
                        )
                        msg_data = json.loads(message)
                        if msg_data.get("message_id") == selective_message["message_id"]:
                            if i == 1:
                                target_received = True
                            else:
                                others_received += 1
                except asyncio.TimeoutError:
                    pass
                except Exception:
                    pass
            
            if not target_received:
                broadcasting_failures.append("Target client did not receive selective message")
            if others_received > 0:
                broadcasting_failures.append(f"{others_received} non-target clients received selective message")
        
        # Clean up connections
        for client in clients:
            try:
                await client["websocket"].close()
            except Exception:
                pass
        
    except Exception as e:
        broadcasting_failures.append(f"Multi-client broadcasting test failed: {e}")
    
    if broadcasting_failures:
        failure_report = ["📡 Broadcasting Failures:"]
        for failure in broadcasting_failures:
            failure_report.append(f"  - {failure}")
        
        pytest.fail(f"Multi-client broadcasting test failed:\n" + "\n".join(failure_report))
    
    print("✅ Multi-client broadcasting test passed")


@pytest.mark.e2e
@pytest.mark.asyncio 
async def test_websocket_connection_resilience():
    """Test WebSocket connection resilience and reconnection handling.
    
    This test should FAIL until connection resilience is properly implemented.
    """
    
    websocket_url = "ws://localhost:8000/websocket"
    resilience_failures = []
    
    print("🔧 Testing WebSocket connection resilience...")
    
    try:
        # Test connection recovery
        connection_attempts = 0
        max_attempts = 5
        
        while connection_attempts < max_attempts:
            try:
                async with websockets.connect(
                    websocket_url,
                    ping_timeout=5,
                    close_timeout=5
                ) as websocket:
                    connection_attempts += 1
                    
                    # Send test message
                    test_msg = {
                        "type": "resilience_test",
                        "attempt": connection_attempts,
                        "timestamp": time.time()
                    }
                    
                    await websocket.send(json.dumps(test_msg))
                    
                    # Simulate connection stress
                    if connection_attempts < 3:
                        print(f"🔄 Connection attempt {connection_attempts} - simulating disconnect")
                        await websocket.close()
                        await asyncio.sleep(1)  # Brief delay before reconnect
                    else:
                        print(f"✅ Stable connection achieved on attempt {connection_attempts}")
                        
                        # Test message after reconnection
                        recovery_msg = {
                            "type": "recovery_test",
                            "message": "Connection recovered successfully",
                            "timestamp": time.time()
                        }
                        
                        await websocket.send(json.dumps(recovery_msg))
                        
                        # Wait for response
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                            print("✅ Message sent successfully after reconnection")
                        except asyncio.TimeoutError:
                            resilience_failures.append("No response after connection recovery")
                        
                        break
                        
            except Exception as e:
                resilience_failures.append(f"Connection attempt {connection_attempts + 1} failed: {e}")
                break
        
        if connection_attempts >= max_attempts:
            resilience_failures.append("Failed to establish stable connection within max attempts")
    
    except Exception as e:
        resilience_failures.append(f"Connection resilience test failed: {e}")
    
    if resilience_failures:
        failure_report = ["🔧 Connection Resilience Failures:"]
        for failure in resilience_failures:
            failure_report.append(f"  - {failure}")
        
        pytest.fail(f"WebSocket resilience test failed:\n" + "\n".join(failure_report))
    
    print("✅ WebSocket resilience test passed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])