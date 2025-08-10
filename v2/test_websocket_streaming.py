"""
Test script to verify WebSocket streaming updates are working properly
"""
import asyncio
import json
import websockets
import requests
from datetime import datetime

# Configuration
API_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws"

async def test_websocket_streaming():
    """Test WebSocket connection and message streaming"""
    
    # First, login to get a token
    print("1. Logging in to get authentication token...")
    login_response = requests.post(
        f"{API_URL}/api/auth/login",
        json={"username": "test_user", "password": "test_password"}
    )
    
    if login_response.status_code != 200:
        print(f"Login failed: {login_response.text}")
        return
    
    token = login_response.json()["access_token"]
    print(f"✅ Got token: {token[:20]}...")
    
    # Connect to WebSocket with token
    print("\n2. Connecting to WebSocket...")
    ws_url_with_token = f"{WS_URL}?token={token}"
    
    try:
        async with websockets.connect(ws_url_with_token) as websocket:
            print("✅ Connected to WebSocket")
            
            # Create a task to listen for messages
            async def listen_for_messages():
                """Listen for incoming WebSocket messages"""
                while True:
                    try:
                        message = await websocket.recv()
                        data = json.loads(message)
                        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
                        
                        # Display different message types
                        msg_type = data.get("type", "unknown")
                        if msg_type == "sub_agent_update":
                            payload = data.get("payload", {})
                            agent_name = payload.get("sub_agent_name", "Unknown")
                            print(f"[{timestamp}] 🤖 Sub-agent update: {agent_name}")
                            if payload.get("state", {}).get("messages"):
                                for msg in payload["state"]["messages"]:
                                    print(f"    📝 {msg.get('content', '')}")
                        elif msg_type == "agent_log":
                            payload = data.get("payload", {})
                            level = payload.get("level", "info")
                            msg = payload.get("message", "")
                            agent = payload.get("sub_agent_name", "System")
                            icon = "❌" if level == "error" else "⚠️" if level == "warning" else "ℹ️"
                            print(f"[{timestamp}] {icon} [{agent}] {msg}")
                        elif msg_type == "tool_call":
                            payload = data.get("payload", {})
                            tool = payload.get("tool_name", "Unknown")
                            agent = payload.get("sub_agent_name", "System")
                            print(f"[{timestamp}] 🔧 [{agent}] Calling tool: {tool}")
                        elif msg_type == "tool_result":
                            payload = data.get("payload", {})
                            tool = payload.get("tool_name", "Unknown")
                            result = str(payload.get("result", ""))[:100]
                            print(f"[{timestamp}] ✅ Tool {tool} result: {result}...")
                        elif msg_type == "error":
                            payload = data.get("payload", {})
                            error = payload.get("error", "Unknown error")
                            agent = payload.get("sub_agent_name", "System")
                            print(f"[{timestamp}] ❌ [{agent}] Error: {error}")
                        elif msg_type == "agent_started":
                            print(f"[{timestamp}] 🚀 Agent started processing")
                        elif msg_type == "agent_completed":
                            print(f"[{timestamp}] ✅ Agent completed processing")
                        else:
                            print(f"[{timestamp}] 📨 {msg_type}: {json.dumps(data)[:100]}...")
                            
                    except websockets.exceptions.ConnectionClosed:
                        print("WebSocket connection closed")
                        break
                    except Exception as e:
                        print(f"Error receiving message: {e}")
            
            # Start listening in background
            listen_task = asyncio.create_task(listen_for_messages())
            
            # Send a test message to trigger agent processing
            print("\n3. Sending test message to trigger agent processing...")
            test_message = {
                "type": "user_message",
                "payload": {
                    "text": "Analyze the system performance and provide optimization recommendations"
                }
            }
            
            await websocket.send(json.dumps(test_message))
            print("✅ Test message sent")
            print("\n4. Listening for streaming updates...\n")
            print("-" * 60)
            
            # Wait for messages for 30 seconds
            await asyncio.sleep(30)
            
            print("-" * 60)
            print("\n✅ Test completed")
            
    except Exception as e:
        print(f"❌ WebSocket connection failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket Streaming Test")
    print("=" * 60)
    asyncio.run(test_websocket_streaming())