#!/usr/bin/env python3
"""
WebSocket CORS origin test
"""
import asyncio
import json
import websockets
from websockets.exceptions import WebSocketException


async def test_websocket_with_origins():
    """Test WebSocket with various origin headers."""
    
    test_cases = [
        {
            "description": "No origin header",
            "url": "ws://localhost:8000/ws",
            "origin": None
        },
        {
            "description": "Valid localhost:3000 origin",
            "url": "ws://localhost:8000/ws",
            "origin": "http://localhost:3000"
        },
        {
            "description": "Valid localhost:3001 origin",
            "url": "ws://localhost:8000/ws",
            "origin": "http://localhost:3001"
        },
        {
            "description": "Invalid origin",
            "url": "ws://localhost:8000/ws",
            "origin": "http://invalid-origin.com"
        },
        {
            "description": "Valid development port",
            "url": "ws://localhost:8000/ws", 
            "origin": "http://localhost:4000"
        }
    ]
    
    for case in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {case['description']}")
        print(f"URL: {case['url']}")
        print(f"Origin: {case['origin']}")
        print(f"{'='*60}")
        
        try:
            # Create connection arguments
            connect_args = {}
            if case['origin']:
                connect_args["origin"] = case['origin']
            
            # Attempt WebSocket connection with timeout
            websocket = await asyncio.wait_for(
                websockets.connect(case['url'], **connect_args),
                timeout=5
            )
            
            try:
                print("SUCCESS: WebSocket connection established!")
                print(f"WebSocket state: {websocket.state}")
                
                # Send a ping
                ping_msg = json.dumps({"type": "ping"})
                await websocket.send(ping_msg)
                print("SUCCESS: Ping message sent")
                
                # Wait for response
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3)
                    print(f"SUCCESS: Response received: {response[:100]}...")
                except asyncio.TimeoutError:
                    print("WARNING: No response within timeout")
                    
            finally:
                await websocket.close()
                
        except WebSocketException as e:
            error_str = str(e)
            if "403" in error_str:
                print(f"ERROR: 403 FORBIDDEN - {error_str}")
            elif "404" in error_str:
                print(f"ERROR: 404 NOT FOUND - {error_str}")
            else:
                print(f"ERROR: WebSocket error - {error_str}")
                
        except Exception as e:
            print(f"ERROR: Connection failed - {e}")


if __name__ == "__main__":
    asyncio.run(test_websocket_with_origins())