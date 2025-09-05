#!/usr/bin/env python
"""Test WebSocket message flow"""

import asyncio
import json
import websockets
import uuid
from datetime import datetime
from shared.isolated_environment import IsolatedEnvironment

async def test_websocket_message():
    uri = "ws://localhost:8000/ws"
    user_id = f"test-user-{uuid.uuid4().hex[:8]}"
    thread_id = f"thread_{uuid.uuid4().hex[:16]}"
    
    print(f"Connecting to WebSocket as user: {user_id}")
    
    async with websockets.connect(uri) as websocket:
        # Send auth message
        auth_msg = {
            "type": "auth",
            "payload": {
                "user_id": user_id,
                "token": "test-token"
            }
        }
        await websocket.send(json.dumps(auth_msg))
        print(f"Sent auth message")
        
        # Wait for auth response
        response = await websocket.recv()
        print(f"Auth response: {response}")
        
        # Send start_agent message
        start_agent_msg = {
            "type": "start_agent",
            "payload": {
                "user_request": "Help me optimize my AI costs. I'm currently spending $3000/month on GPT-4.",
                "thread_id": thread_id,
                "context": {},
                "settings": {}
            }
        }
        
        print(f"Sending start_agent message...")
        await websocket.send(json.dumps(start_agent_msg))
        
        # Listen for responses
        print("Listening for responses...")
        try:
            for i in range(30):  # Listen for 30 seconds
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    response_data = json.loads(response)
                    print(f"Response {i}: {response_data.get('type', 'unknown')} - {str(response_data)[:200]}")
                    
                    # Check for agent completion
                    if response_data.get('type') in ['agent_completed', 'error']:
                        print("Agent execution completed or errored")
                        break
                except asyncio.TimeoutError:
                    print(".", end="", flush=True)
                    continue
        except Exception as e:
            print(f"\nError receiving message: {e}")
        
        print("\nTest completed")

if __name__ == "__main__":
    asyncio.run(test_websocket_message())