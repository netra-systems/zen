#!/usr/bin/env python3
"""
Debug WebSocket Message Structure
Quick test to see what messages are sent back by WebSocket endpoint
"""

import asyncio
import websockets
import json
import sys

async def test_websocket_message():
    uri = "wss://netra-backend-staging-pnovr5vsba-uc.a.run.app/api/v1/websocket"

    try:
        async with websockets.connect(uri) as websocket:
            # Send a tool_executing test message
            test_message = {
                "type": "tool_executing",
                "tool_name": "search_tool",
                "parameters": {"query": "test", "max_results": 10},
                "user_id": "test_user_123"
            }

            print(f"Sending: {json.dumps(test_message, indent=2)}")
            await websocket.send(json.dumps(test_message))

            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                response_data = json.loads(response)
                print(f"Received: {json.dumps(response_data, indent=2)}")

                # Check if tool_name is at root level or in data
                if "tool_name" in response_data:
                    print("✅ tool_name found at ROOT level")
                elif "data" in response_data and isinstance(response_data["data"], dict) and "tool_name" in response_data["data"]:
                    print("❌ tool_name found in DATA field")
                else:
                    print("❓ tool_name not found anywhere")

            except asyncio.TimeoutError:
                print("⏱️ No response received within 5 seconds")

    except Exception as e:
        print(f"❌ Connection failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket_message())