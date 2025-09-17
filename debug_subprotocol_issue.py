#!/usr/bin/env python3
"""
Debug WebSocket Subprotocol Negotiation Issue #886

This script will test the exact subprotocol negotiation failure
to understand what's going wrong.
"""

import asyncio
import websockets
import sys
import time

STAGING_WEBSOCKET_URL = "wss://netra-backend-staging-701982941522.us-central1.run.app/ws"

async def test_subprotocol_negotiation():
    """Test different subprotocol combinations to identify the issue."""
    
    # Test cases to try
    test_cases = [
        {
            "name": "No subprotocols",
            "subprotocols": None,
            "expected": "Should accept without subprotocol"
        },
        {
            "name": "jwt-auth only",  
            "subprotocols": ["jwt-auth"],
            "expected": "Should accept jwt-auth"
        },
        {
            "name": "staging-auth only",
            "subprotocols": ["staging-auth"],
            "expected": "Should accept staging-auth"
        },
        {
            "name": "e2e-testing only",
            "subprotocols": ["e2e-testing"],
            "expected": "Should accept e2e-testing"
        },
        {
            "name": "Multiple supported",
            "subprotocols": ["jwt-auth", "staging-auth"],
            "expected": "Should accept first supported"
        },
        {
            "name": "Unsupported protocol",
            "subprotocols": ["unsupported-protocol"],
            "expected": "Should fail with no subprotocols supported"
        }
    ]
    
    for test_case in test_cases:
        print(f"\n=== Testing: {test_case['name']} ===")
        print(f"Subprotocols: {test_case['subprotocols']}")
        print(f"Expected: {test_case['expected']}")
        
        try:
            # Attempt connection
            connect_kwargs = {
                "ping_timeout": 5,
                "close_timeout": 5
            }
            
            if test_case['subprotocols']:
                connect_kwargs["subprotocols"] = test_case['subprotocols']
            
            async with websockets.connect(STAGING_WEBSOCKET_URL, **connect_kwargs) as websocket:
                print(f" SUCCESS: Connected with subprotocol: {websocket.subprotocol}")
                
                # Try to send a simple message
                await websocket.send('{"type": "ping"}')
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print(f" SUCCESS: Received response: {response[:100]}...")
                except asyncio.TimeoutError:
                    print(" INFO: No immediate response (normal for unauthenticated)")
                    
                print(" SUCCESS: Connection established and working")
                
        except websockets.NegotiationError as e:
            print(f" FAIL: Negotiation error: {e}")
            if "no subprotocols supported" in str(e):
                print(" INFO: This confirms the subprotocol negotiation issue!")
                
        except websockets.InvalidStatus as e:
            print(f" INFO: HTTP error (likely auth-related): {e}")
            
        except Exception as e:
            print(f" ERROR: Unexpected error: {e}")
        
        # Small delay between tests
        await asyncio.sleep(0.5)

async def main():
    """Main test function."""
    print("WebSocket Subprotocol Negotiation Debugging")
    print("=" * 50)
    print(f"Testing URL: {STAGING_WEBSOCKET_URL}")
    
    await test_subprotocol_negotiation()
    
    print("\n" + "=" * 50)
    print("Debugging complete.")

if __name__ == "__main__":
    asyncio.run(main())