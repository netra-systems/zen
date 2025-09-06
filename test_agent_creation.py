#!/usr/bin/env python3
"""Test agent creation flow directly."""

import asyncio
import websockets
import json
import uuid
from shared.isolated_environment import IsolatedEnvironment

async def test_agent_creation():
    """Test WebSocket connection and agent creation."""
    
    # Create unique IDs for testing
    thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
    user_id = f"test_user_{uuid.uuid4().hex[:8]}"
    
    ws_url = "ws://localhost:8000/ws"
    print(f"🔌 Connecting to {ws_url}")
    
    try:
        # Connect with dev-temp auth in URL
        auth_url = f"{ws_url}?user_id={user_id}&auth_type=dev-temp"
        
        async with websockets.connect(auth_url) as websocket:
            print("✅ WebSocket connected")
            
            # Send start_agent message
            message = {
                "type": "start_agent",
                "payload": {
                    "user_request": "Test agent creation flow",
                    "thread_id": thread_id,
                    "context": {},
                    "settings": {}
                }
            }
            
            print(f"📤 Sending: {json.dumps(message, indent=2)}")
            await websocket.send(json.dumps(message))
            
            # Listen for responses
            print("\n📥 Waiting for responses...")
            timeout = 10  # seconds
            start_time = asyncio.get_event_loop().time()
            
            while True:
                try:
                    remaining = timeout - (asyncio.get_event_loop().time() - start_time)
                    if remaining <= 0:
                        print("⏱️ Timeout reached")
                        break
                        
                    response = await asyncio.wait_for(
                        websocket.recv(), 
                        timeout=min(remaining, 1)
                    )
                    
                    data = json.loads(response)
                    msg_type = data.get('type', 'unknown')
                    
                    if msg_type == 'error':
                        print(f"❌ Error: {data.get('payload', {}).get('message', 'Unknown error')}")
                    elif msg_type == 'agent_completed':
                        print(f"✅ Agent completed: {data.get('payload', {}).get('result', 'No result')}")
                    elif msg_type == 'agent_thinking':
                        print(f"🤔 Agent thinking: {data.get('payload', {}).get('thought', '')[:100]}")
                    elif msg_type == 'tool_executing':
                        print(f"🔧 Tool executing: {data.get('payload', {}).get('tool_name', 'unknown')}")
                    else:
                        print(f"📨 {msg_type}: {str(data.get('payload', ''))[:100]}")
                        
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    print(f"⚠️ Error receiving: {e}")
                    break
                    
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False
    
    print("\n✅ Test complete")
    return True

if __name__ == "__main__":
    result = asyncio.run(test_agent_creation())
    exit(0 if result else 1)