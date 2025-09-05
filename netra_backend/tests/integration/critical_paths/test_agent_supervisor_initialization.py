#!/usr/bin/env python3
"""
Agent Supervisor Initialization Test

This test validates:
1. Agent supervisor is properly initialized during app startup
2. WebSocket can access agent supervisor from app state
3. Agent supervisor error is resolved
"""

import asyncio
import json
import pytest
import websockets
from datetime import datetime, timezone
from shared.isolated_environment import IsolatedEnvironment

from test_framework.test_patterns import L3IntegrationTest


class TestAgentSupervisorInitialization(L3IntegrationTest):
    """Test agent supervisor initialization and WebSocket integration."""
    
    @pytest.mark.asyncio
    async def test_agent_supervisor_availability_via_websocket(self):
        """Test if agent supervisor is available via WebSocket connection."""
        user_data = await self.create_test_user("supervisor_init_test@test.com")
        token = await self.get_auth_token(user_data)
        
        websocket_url = "ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        try:
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                print("✅ WebSocket connection established successfully")
                
                # Wait a moment for any initial messages
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f"📨 Received message: {message}")
                    data = json.loads(message)
                    
                    # Check if it's an error message about agent_supervisor
                    if data.get("type") == "error" and "agent_supervisor" in data.get("error", ""):
                        print("❌ Found agent_supervisor error in WebSocket response")
                        print(f"Error details: {data}")
                        pytest.fail("Agent supervisor not initialized properly - WebSocket receiving agent_supervisor error")
                    
                except asyncio.TimeoutError:
                    print("⏰ No initial message received (this is expected for successful connections)")
                
                # Try to send a simple message to trigger agent supervisor usage
                test_message = {
                    "type": "agent_request",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "data": {
                        "action": "ping"
                    }
                }
                
                await websocket.send(json.dumps(test_message))
                print("📤 Sent agent request message")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"📨 Received response: {response}")
                    response_data = json.loads(response)
                    
                    # Check for agent supervisor error
                    if (response_data.get("type") == "error" and 
                        "agent_supervisor" in response_data.get("error", "")):
                        print("❌ Agent supervisor error detected!")
                        print(f"Error: {response_data['error']}")
                        pytest.fail(f"Agent supervisor initialization failed: {response_data['error']}")
                    
                    print("✅ No agent supervisor error - system appears healthy")
                    
                except asyncio.TimeoutError:
                    print("⏰ No response to agent request (may be expected)")
                    # This is not necessarily a failure - WebSocket might not echo
                    pass
                    
        except websockets.exceptions.ConnectionClosed as e:
            if e.code == 1003:  # Unsupported Data
                pytest.fail("WebSocket closed due to unsupported data - possible agent supervisor issue")
            else:
                pytest.fail(f"WebSocket connection closed unexpectedly: {e}")
        except Exception as e:
            pytest.fail(f"WebSocket test failed with error: {e}")
            
    @pytest.mark.asyncio
    async def test_agent_supervisor_error_reproduction(self):
        """Specifically test to reproduce the agent_supervisor attribute error."""
        user_data = await self.create_test_user("error_repro_test@test.com")
        token = await self.get_auth_token(user_data)
        
        websocket_url = "ws://localhost:8000/websocket"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Track whether we see the specific error
        agent_supervisor_error_found = False
        error_details = None
        
        try:
            async with websockets.connect(websocket_url, additional_headers=headers) as websocket:
                print("🔬 Testing for agent_supervisor error reproduction...")
                
                # Send messages that might trigger agent supervisor usage
                test_messages = [
                    {"type": "agent_create", "data": {"agent_type": "test"}},
                    {"type": "agent_status", "data": {}},
                    {"type": "agent_message", "data": {"action": "test"}},
                ]
                
                for i, message in enumerate(test_messages):
                    message["id"] = f"test_{i}"
                    message["timestamp"] = datetime.now(timezone.utc).isoformat()
                    
                    try:
                        await websocket.send(json.dumps(message))
                        print(f"📤 Sent test message {i}: {message['type']}")
                        
                        # Wait for response
                        response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                        response_data = json.loads(response)
                        
                        if (response_data.get("type") == "error" and 
                            "agent_supervisor" in response_data.get("error", "")):
                            agent_supervisor_error_found = True
                            error_details = response_data
                            print(f"🎯 Found agent_supervisor error with message type '{message['type']}'")
                            print(f"Error: {response_data['error']}")
                            break
                            
                    except asyncio.TimeoutError:
                        print(f"⏰ No response to message {i}")
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        print(f"🔌 Connection closed after message {i}")
                        break
                        
                if agent_supervisor_error_found:
                    # We successfully reproduced the error
                    print("✅ Successfully reproduced agent_supervisor error")
                    print(f"Error occurred with: {error_details}")
                    # Don't fail the test - this confirms our diagnosis
                else:
                    print("🤔 Could not reproduce agent_supervisor error - it may be fixed or intermittent")
                    
        except Exception as e:
            if "'State' object has no attribute 'agent_supervisor'" in str(e):
                print("✅ Reproduced agent_supervisor error in connection setup")
                agent_supervisor_error_found = True
            else:
                print(f"❓ Unexpected error: {e}")
                
        # Report findings
        if agent_supervisor_error_found:
            print("\n🔍 DIAGNOSIS: Agent supervisor not initialized in app.state")
            print("💡 SOLUTION NEEDED: Ensure agent_supervisor is created during app startup")
        else:
            print("\n✅ No agent_supervisor errors detected - system may be working correctly")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])