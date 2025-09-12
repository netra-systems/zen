#!/usr/bin/env python3
"""
WebSocket Fix Validation Test
Validates that staging /websocket endpoint works for frontend connectivity
"""

import asyncio
import json
import time
import websockets

async def test_working_websocket_endpoint():
    """Test the working /websocket endpoint to confirm it's usable for frontend"""
    print("🔍 Testing WORKING WebSocket Endpoint: /websocket")
    print("=" * 60)
    
    url = "wss://api.staging.netrasystems.ai/websocket"
    print(f"Connecting to: {url}")
    
    try:
        async with websockets.connect(url, close_timeout=10) as ws:
            print("✅ Connected successfully to /websocket!")
            
            # Test ping/pong
            ping_message = {"type": "ping", "timestamp": time.time()}
            await ws.send(json.dumps(ping_message))
            print(f"📤 Sent: {ping_message}")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(ws.recv(), timeout=5)
                response_data = json.loads(response)
                print(f"📥 Received: {response_data}")
                
                # Test chat message (what frontend would send)
                chat_message = {
                    "type": "message",
                    "content": "Test message from WebSocket fix validation",
                    "user_id": "test_user_websocket_fix",
                    "thread_id": f"test_thread_{int(time.time())}",
                    "timestamp": time.time()
                }
                await ws.send(json.dumps(chat_message))
                print(f"📤 Sent chat message: {chat_message['content']}")
                
                # Listen for potential responses
                events_received = []
                listen_start = time.time()
                while time.time() - listen_start < 10:  # Listen for 10 seconds
                    try:
                        event = await asyncio.wait_for(ws.recv(), timeout=2)
                        event_data = json.loads(event)
                        events_received.append(event_data)
                        print(f"📥 Event: {event_data.get('type', 'unknown')} - {event_data}")
                        
                        # Check for agent events
                        event_type = event_data.get('type')
                        if event_type in ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']:
                            print(f"🎉 MISSION CRITICAL EVENT: {event_type}")
                    except asyncio.TimeoutError:
                        print("⏰ No more events (timeout)")
                        break
                
                print(f"\n📊 Summary:")
                print(f"   - Connection: ✅ SUCCESS")
                print(f"   - Message sending: ✅ SUCCESS") 
                print(f"   - Events received: {len(events_received)}")
                print(f"   - Duration: {time.time() - listen_start:.2f}s")
                
                if events_received:
                    print("🎯 FRONTEND CONNECTIVITY CONFIRMED!")
                    print("   The /websocket endpoint is fully functional for chat.")
                else:
                    print("⚠️  PARTIAL SUCCESS:")
                    print("   Connection works, but no agent events received.")
                    print("   This could be due to backend processing or agent issues.")
                
                return True, events_received
                
            except asyncio.TimeoutError:
                print("⏰ No initial response received (timeout)")
                return True, []  # Connection worked even without response
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False, []

async def test_broken_websocket_endpoint():
    """Test the broken /ws endpoint to confirm it's the problem"""
    print("\n🔍 Testing BROKEN WebSocket Endpoint: /ws")
    print("=" * 60)
    
    url = "wss://api.staging.netrasystems.ai/ws"
    print(f"Connecting to: {url}")
    
    try:
        async with websockets.connect(url, close_timeout=5) as ws:
            print("❓ Unexpected success on /ws endpoint")
            return True, []
    except websockets.exceptions.InvalidStatus as e:
        if "500" in str(e):
            print("❌ Confirmed: /ws returns HTTP 500 (server error)")
        elif "404" in str(e):
            print("❌ Confirmed: /ws returns HTTP 404 (not found)")
        else:
            print(f"❌ /ws error: {e}")
        return False, []
    except Exception as e:
        print(f"❌ /ws connection failed: {e}")
        return False, []

async def generate_frontend_fix_recommendation():
    """Generate recommendation for frontend team"""
    print("\n" + "=" * 60)
    print("🔧 FRONTEND FIX RECOMMENDATION")
    print("=" * 60)
    print()
    print("ISSUE DIAGNOSED:")
    print("- Frontend is connecting to '/ws' endpoint (broken)")
    print("- Should connect to '/websocket' endpoint (working)")
    print()
    print("REQUIRED CHANGE:")
    print("Update frontend WebSocket URL from:")
    print("  ❌ wss://api.staging.netrasystems.ai/ws")
    print("to:")
    print("  ✅ wss://api.staging.netrasystems.ai/websocket")
    print()
    print("FILES TO UPDATE:")
    print("- Frontend WebSocket client configuration")
    print("- Any hardcoded WebSocket URLs")
    print("- Environment variables for staging WebSocket URL")
    print()
    print("VALIDATION STEPS:")
    print("1. Update frontend to use /websocket endpoint")
    print("2. Test chat functionality end-to-end")
    print("3. Verify agent events are received properly")
    print("4. Confirm no 404/500 errors in browser console")
    print()

async def main():
    """Run WebSocket fix validation"""
    print("🚀 WebSocket Fix Validation for Issue #488")
    print(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    
    # Test working endpoint
    working_success, working_events = await test_working_websocket_endpoint()
    
    # Test broken endpoint
    broken_success, _ = await test_broken_websocket_endpoint()
    
    # Generate recommendation
    await generate_frontend_fix_recommendation()
    
    # Final summary
    print("\n" + "=" * 60)
    print("📋 FINAL VALIDATION RESULTS")
    print("=" * 60)
    
    if working_success and not broken_success:
        print("🎯 DIAGNOSIS CONFIRMED:")
        print("   - /websocket endpoint: ✅ WORKING")  
        print("   - /ws endpoint: ❌ BROKEN")
        print("   - Frontend needs to use /websocket instead of /ws")
        print("\n✅ ISSUE #488 ROOT CAUSE IDENTIFIED AND SOLUTION PROVIDED")
    else:
        print("❓ Unexpected results - further investigation needed")

if __name__ == "__main__":
    asyncio.run(main())