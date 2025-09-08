#!/usr/bin/env python3
"""
Simple WebSocket Debug - No Unicode characters for Windows compatibility
"""

import asyncio
import websockets
import json
import time
import traceback
from tests.e2e.staging_test_config import get_staging_config

async def debug_websocket():
    """Debug WebSocket connection step by step."""
    
    print("=" * 50)
    print("WEBSOCKET DEBUG - FIVE WHYS ANALYSIS")
    print("=" * 50)
    
    config = get_staging_config()
    print(f"Backend URL: {config.backend_url}")
    print(f"WebSocket URL: {config.websocket_url}")
    print()
    
    # Check backend health
    print("1. BACKEND HEALTH CHECK:")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{config.backend_url}/health")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print("   [OK] Backend is healthy")
            else:
                print("   [ERROR] Backend not healthy")
                return
    except Exception as e:
        print(f"   [ERROR] Backend health check failed: {e}")
        return
    print()
    
    # Test WebSocket with auth
    print("2. WEBSOCKET CONNECTION TEST:")
    try:
        headers = config.get_websocket_headers()
        print(f"   Auth headers: {len(headers)} headers")
        print(f"   Has Authorization: {'Authorization' in headers}")
        
        print("   Connecting to WebSocket...")
        connection_start = time.time()
        
        async with websockets.connect(
            config.websocket_url,
            additional_headers=headers,
            close_timeout=10,
            open_timeout=10
        ) as ws:
            connection_time = time.time() - connection_start
            print(f"   [OK] Connected in {connection_time:.3f}s")
            
            # Wait for welcome message
            print("   Waiting for welcome message...")
            message_start = time.time()
            
            try:
                welcome_response = await asyncio.wait_for(ws.recv(), timeout=15)
                message_time = time.time() - message_start
                
                print(f"   [OK] Message received in {message_time:.3f}s")
                print(f"   Message: {welcome_response[:100]}...")
                
                # Parse the message
                try:
                    message_data = json.loads(welcome_response)
                    event_type = message_data.get('event', 'unknown')
                    print(f"   Event type: {event_type}")
                    
                    if event_type == 'connection_established':
                        print("   [SUCCESS] Connection established message received!")
                        return True
                    else:
                        print(f"   [WARN] Unexpected event: {event_type}")
                        
                except json.JSONDecodeError:
                    print(f"   [WARN] Non-JSON message: {welcome_response}")
                    
            except asyncio.TimeoutError:
                print("   [ERROR] TIMEOUT - No message received within 15s")
                print("   Connection established but server didn't send welcome message")
                return False
                
            except websockets.exceptions.ConnectionClosed as e:
                message_time = time.time() - message_start
                print(f"   [ERROR] CONNECTION CLOSED after {message_time:.3f}s")
                print(f"   Close code: {e.code}")
                print(f"   Close reason: {e.reason}")
                
                # Analyze close codes
                if e.code == 1006:
                    print("   Analysis: 1006 = Abnormal closure (network/server issue)")
                elif e.code == 1008:
                    print("   Analysis: 1008 = Policy violation (auth failure)")
                elif e.code == 1011:
                    print("   Analysis: 1011 = Internal server error")
                else:
                    print(f"   Analysis: Unknown close code {e.code}")
                return False
                
    except websockets.exceptions.InvalidStatus as e:
        print(f"   [ERROR] AUTH REJECTED: {e}")
        return False
        
    except Exception as e:
        print(f"   [ERROR] CONNECTION FAILED: {e}")
        print(f"   Error type: {type(e).__name__}")
        traceback.print_exc()
        return False
    
    print()
    return False

if __name__ == "__main__":
    result = asyncio.run(debug_websocket())
    print(f"\nResult: {'SUCCESS' if result else 'FAILED'}")