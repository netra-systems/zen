#!/usr/bin/env python3
"""Test WebSocket agent execution flow."""

import asyncio
import json
import websockets
import requests


def get_google_auth_token():
    """Get authentication token using Google OAuth flow."""
    # First, initiate the Google OAuth login
    auth_response = requests.get("http://localhost:8000/auth/google")
    
    # For development/testing, we can use a pre-configured test token
    # In production, this would go through the full OAuth flow
    print("📱 Please authenticate via Google OAuth in your browser")
    print("   Visit: http://localhost:3000")
    print("   Click 'Sign in with Google' and complete authentication")
    
    # For now, let's try to get a dev token if available
    dev_login_response = requests.post(
        "http://localhost:8000/api/auth/dev-login",
        json={"email": "dev@netra.ai", "name": "Dev User"}
    )
    
    if dev_login_response.status_code == 200:
        token_data = dev_login_response.json()
        return token_data.get("access_token")
    
    return None


async def test_agent_execution():
    """Test sending a message through WebSocket to trigger agent flow."""
    # Get authentication token
    token = get_google_auth_token()
    
    if not token:
        print("⚠️  No authentication token available")
        print("   Please ensure you're logged in via Google OAuth")
        return
    
    # Connect with proper authentication
    uri = "ws://localhost:8000/ws/chat"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    try:
        async with websockets.connect(uri, additional_headers=headers) as websocket:
            print("✅ Connected to WebSocket")
            
            # Send start_agent message
            message = {
                "type": "start_agent",
                "payload": {
                    "user_request": "Help me optimize my AI costs",
                    "mode": "chat"
                }
            }
            
            print(f"📤 Sending message: {json.dumps(message, indent=2)}")
            await websocket.send(json.dumps(message))
            
            # Listen for responses
            print("📥 Waiting for responses...")
            timeout = 30  # 30 second timeout
            start_time = asyncio.get_event_loop().time()
            
            while asyncio.get_event_loop().time() - start_time < timeout:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    response_data = json.loads(response)
                    print(f"📨 Received: {json.dumps(response_data, indent=2)}")
                    
                    # Check for completion
                    if response_data.get("type") == "agent_completed":
                        print("✅ Agent completed successfully!")
                        break
                    elif response_data.get("type") == "error":
                        print(f"❌ Error: {response_data}")
                        break
                        
                except asyncio.TimeoutError:
                    # Continue waiting
                    continue
                except websockets.exceptions.ConnectionClosed:
                    print("❌ WebSocket connection closed")
                    break
                    
    except Exception as e:
        print(f"❌ Failed to connect: {e}")


if __name__ == "__main__":
    print("🚀 Testing WebSocket agent execution...")
    asyncio.run(test_agent_execution())
    print("✅ Test complete")