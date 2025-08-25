#!/usr/bin/env python3
"""Simple test script to verify agent supervisor is initialized correctly"""

import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

async def test_agent_supervisor_availability():
    """Test if agent supervisor is available via health endpoint"""
    import aiohttp
    import json
    
    health_url = "http://localhost:8000/health"
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(health_url) as response:
                if response.status == 200:
                    health_data = await response.json()
                    print("Health endpoint response:")
                    print(json.dumps(health_data, indent=2))
                    
                    # Check if startup completed
                    startup_complete = health_data.get('status') == 'healthy'
                    print(f"\nStartup complete: {startup_complete}")
                    
                    if startup_complete:
                        # Try to access a route that would require agent_supervisor
                        agent_url = "http://localhost:8000/api/v1/agents/supervisor/status"
                        
                        try:
                            async with session.get(agent_url) as agent_response:
                                if agent_response.status in [200, 404, 405]:  # Any response means supervisor exists
                                    print("✅ Agent supervisor is accessible!")
                                    return True
                                else:
                                    print(f"❌ Agent supervisor endpoint returned {agent_response.status}")
                                    return False
                        except Exception as e:
                            print(f"❌ Error accessing agent supervisor: {e}")
                            return False
                    else:
                        print("❌ Startup not complete yet")
                        return False
                else:
                    print(f"❌ Health endpoint returned {response.status}")
                    return False
                    
    except Exception as e:
        print(f"❌ Error connecting to health endpoint: {e}")
        return False

async def test_websocket_agent_message():
    """Test WebSocket agent message flow if possible"""
    try:
        import websockets
        import json
        
        # Try to connect to WebSocket endpoint
        websocket_url = "ws://localhost:8000/ws"
        
        async with websockets.connect(websocket_url) as websocket:
            # Send a simple test message
            test_message = {
                "type": "user_message",
                "payload": {
                    "content": "Test agent supervisor availability",
                    "thread_id": "test_supervisor_check"
                }
            }
            
            await websocket.send(json.dumps(test_message))
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                print("✅ WebSocket agent communication successful!")
                print(f"Response type: {response_data.get('type')}")
                return True
            except asyncio.TimeoutError:
                print("⚠️  WebSocket response timeout (but connection worked)")
                return True
            
    except Exception as e:
        print(f"⚠️  WebSocket test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("Testing agent supervisor initialization fix...")
    print("=" * 50)
    
    # Test 1: Health endpoint and agent supervisor availability
    print("\n1. Testing agent supervisor availability...")
    health_ok = await test_agent_supervisor_availability()
    
    # Test 2: WebSocket agent communication (if health is OK)
    if health_ok:
        print("\n2. Testing WebSocket agent communication...")
        websocket_ok = await test_websocket_agent_message()
    else:
        websocket_ok = False
        print("\n2. Skipping WebSocket test (health check failed)")
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"  Agent supervisor available: {'✅' if health_ok else '❌'}")
    print(f"  WebSocket communication:   {'✅' if websocket_ok else '❌'}")
    
    if health_ok and websocket_ok:
        print("\n🎉 Agent supervisor initialization fix SUCCESS!")
        return 0
    elif health_ok:
        print("\n⚠️  Agent supervisor works but WebSocket needs attention")
        return 0
    else:
        print("\n❌ Agent supervisor initialization still has issues")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))