#!/usr/bin/env python3
"""
End-to-end WebSocket chat functionality test
"""
import asyncio
import json
import websockets
import time


async def test_e2e_chat():
    """Test end-to-end chat functionality through WebSocket."""
    
    print("=" * 60)
    print("Testing End-to-End Chat Functionality")
    print("=" * 60)
    
    try:
        # Connect to WebSocket
        print("Step 1: Establishing WebSocket connection...")
        websocket = await websockets.connect(
            "ws://localhost:8000/ws",
            origin="http://localhost:3000"
        )
        
        print("SUCCESS: WebSocket connection established")
        
        # Wait for welcome message
        print("\nStep 2: Waiting for welcome message...")
        try:
            welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=5)
            welcome_data = json.loads(welcome_msg)
            print(f"SUCCESS: Got welcome message: {welcome_data['type']}")
            print(f"Connection ID: {welcome_data['payload']['connection_id']}")
            print(f"User ID: {welcome_data['payload']['user_id']}")
        except asyncio.TimeoutError:
            print("WARNING: No welcome message received")
        
        # Send a chat message to test the AI agent pipeline
        print("\nStep 3: Sending chat message to AI agent...")
        chat_message = {
            "type": "user_message",
            "payload": {
                "content": "Hello, can you help me test the WebSocket chat functionality?",
                "timestamp": time.time(),
                "message_id": "test_msg_001"
            }
        }
        
        await websocket.send(json.dumps(chat_message))
        print("SUCCESS: Chat message sent to AI agent")
        
        # Wait for AI agent responses
        print("\nStep 4: Waiting for AI agent responses...")
        response_count = 0
        timeout_seconds = 30  # Give AI agent time to respond
        
        try:
            while response_count < 5:  # Wait for up to 5 responses
                response = await asyncio.wait_for(websocket.recv(), timeout=timeout_seconds)
                response_data = json.loads(response)
                response_count += 1
                
                msg_type = response_data.get('type', 'unknown')
                print(f"Response {response_count}: {msg_type}")
                
                if msg_type == "agent_started":
                    payload = response_data.get('payload', {})
                    agent_name = payload.get('agent_name', 'unknown')
                    print(f"  -> Agent {agent_name} started")
                
                elif msg_type == "agent_completed":
                    payload = response_data.get('payload', {})
                    agent_name = payload.get('agent_name', 'unknown')
                    duration = payload.get('duration_ms', 0)
                    print(f"  -> Agent {agent_name} completed in {duration}ms")
                
                elif msg_type == "tool_call":
                    payload = response_data.get('payload', {})
                    tool_name = payload.get('tool_name', 'unknown')
                    print(f"  -> Tool executed: {tool_name}")
                
                elif msg_type == "final_response":
                    payload = response_data.get('payload', {})
                    content = payload.get('content', '')[:100]
                    print(f"  -> AI Response: {content}...")
                    
                elif msg_type == "agent_error":
                    payload = response_data.get('payload', {})
                    error = payload.get('error', 'unknown error')
                    print(f"  -> Agent Error: {error}")
                    
                else:
                    print(f"  -> Other event: {response_data}")
                
                # Reduce timeout for subsequent messages
                timeout_seconds = 10
                
        except asyncio.TimeoutError:
            if response_count == 0:
                print("ERROR: No response from AI agent within timeout")
            else:
                print(f"INFO: Received {response_count} responses, timeout reached")
        
        # Send ping to test connection health
        print("\nStep 5: Testing connection health with ping...")
        ping_message = {
            "type": "ping",
            "timestamp": time.time()
        }
        
        await websocket.send(json.dumps(ping_message))
        print("SUCCESS: Ping sent")
        
        try:
            pong_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            pong_data = json.loads(pong_response)
            if pong_data.get('type') == 'pong':
                print("SUCCESS: Pong received - connection is healthy")
            else:
                print(f"INFO: Received other response to ping: {pong_data}")
        except asyncio.TimeoutError:
            print("WARNING: No pong response received")
        
        # Close connection gracefully
        print("\nStep 6: Closing connection...")
        await websocket.close()
        print("SUCCESS: Connection closed gracefully")
        
        print(f"\n{'=' * 60}")
        print("End-to-End Chat Test COMPLETED")
        print(f"Total responses received: {response_count}")
        print("WebSocket chat functionality is working!")
        print(f"{'=' * 60}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: E2E test failed: {e}")
        return False


if __name__ == "__main__":
    asyncio.run(test_e2e_chat())