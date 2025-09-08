#!/usr/bin/env python3
"""
WebSocket Staging Connection Debug Script
Five Whys Analysis - Debug the exact cause of WebSocket connection failures
"""

import asyncio
import websockets
import json
import time
import traceback
from tests.e2e.staging_test_config import get_staging_config

async def debug_websocket_connection():
    """Debug WebSocket connection step by step to identify the exact failure point."""
    
    print("=" * 70)
    print("WEBSOCKET STAGING DEBUG - FIVE WHYS INVESTIGATION")
    print("=" * 70)
    
    config = get_staging_config()
    
    print(f"1. CONFIGURATION CHECK:")
    print(f"   Backend URL: {config.backend_url}")
    print(f"   WebSocket URL: {config.websocket_url}")
    print(f"   Skip auth: {config.skip_websocket_auth}")
    print()
    
    # Step 1: Check backend health
    print("2. BACKEND HEALTH CHECK:")
    try:
        import httpx
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(f"{config.backend_url}/health")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            if response.status_code != 200:
                print("   [ERROR] Backend health check failed!")
                return
            print("   [OK] Backend is healthy")
    except Exception as e:
        print(f"   [ERROR] Backend health check error: {e}")
        return
    print()
    
    # Step 2: Test connection without auth (expect 403)
    print("3. WEBSOCKET CONNECTION WITHOUT AUTH (expect 403):")
    try:
        async with websockets.connect(
            config.websocket_url,
            close_timeout=5,
            open_timeout=5
        ) as ws:
            print("   ❌ UNEXPECTED: Connection succeeded without auth!")
            return
    except websockets.exceptions.InvalidStatus as e:
        if "403" in str(e) or "401" in str(e):
            print(f"   ✅ Expected auth error: {e}")
        else:
            print(f"   ⚠️ Unexpected status error: {e}")
    except Exception as e:
        print(f"   ⚠️ Unexpected error: {e}")
    print()
    
    # Step 3: Get auth headers and test connection
    print("4. WEBSOCKET CONNECTION WITH AUTH:")
    try:
        headers = config.get_websocket_headers()
        print(f"   Auth headers count: {len(headers)}")
        print(f"   Has Authorization: {'Authorization' in headers}")
        print(f"   Headers: {list(headers.keys())}")
        
        if 'Authorization' in headers:
            auth_token = headers['Authorization']
            print(f"   Token preview: {auth_token[:50]}...{auth_token[-10:]}")
        print()
        
        # Attempt connection with auth
        print("   Attempting WebSocket connection...")
        connection_start = time.time()
        
        async with websockets.connect(
            config.websocket_url,
            additional_headers=headers,
            close_timeout=10,
            open_timeout=10
        ) as ws:
            connection_time = time.time() - connection_start
            print(f"   ✅ Connection established in {connection_time:.3f}s")
            
            # Step 4: Wait for welcome message
            print("   Waiting for welcome message...")
            message_start = time.time()
            
            # Try to receive message with detailed error handling
            try:
                # Set up a longer timeout to capture any delayed messages
                welcome_response = await asyncio.wait_for(ws.recv(), timeout=15)
                message_time = time.time() - message_start
                
                print(f"   ✅ Message received in {message_time:.3f}s")
                print(f"   Message content: {welcome_response}")
                
                # Parse the message
                try:
                    message_data = json.loads(welcome_response)
                    print(f"   Message type: {message_data.get('type', 'unknown')}")
                    print(f"   Event: {message_data.get('event', 'unknown')}")
                    if message_data.get('event') == 'connection_established':
                        print("   ✅ Connection established message received!")
                    else:
                        print(f"   ⚠️ Unexpected message type: {message_data}")
                except json.JSONDecodeError:
                    print(f"   ⚠️ Message is not JSON: {welcome_response}")
                    
            except asyncio.TimeoutError:
                print(f"   ❌ TIMEOUT: No message received within 15 seconds")
                print(f"   Connection was established but server didn't send welcome message")
                
                # Try to check connection state
                print(f"   WebSocket state: {ws.state}")
                print(f"   Connection closed: {ws.closed}")
                
            except websockets.exceptions.ConnectionClosed as e:
                message_time = time.time() - message_start
                print(f"   ❌ CONNECTION CLOSED: {e} after {message_time:.3f}s")
                print(f"   Close code: {e.code}")
                print(f"   Close reason: {e.reason}")
                
                # Analyze close codes
                if e.code == 1006:
                    print("   Analysis: 1006 = Abnormal closure (network issue or server crash)")
                elif e.code == 1008:
                    print("   Analysis: 1008 = Policy violation (auth failure)")
                elif e.code == 1011:
                    print("   Analysis: 1011 = Internal server error")
                else:
                    print(f"   Analysis: Unknown close code {e.code}")
                
            except Exception as e:
                print(f"   ❌ UNEXPECTED ERROR: {e}")
                print(f"   Error type: {type(e).__name__}")
                traceback.print_exc()
        
    except websockets.exceptions.InvalidStatus as e:
        print(f"   ❌ AUTH REJECTED: {e}")
        print(f"   The server rejected our authentication")
        
    except Exception as e:
        print(f"   ❌ CONNECTION FAILED: {e}")
        print(f"   Error type: {type(e).__name__}")
        traceback.print_exc()
    
    print()
    print("=" * 70)
    print("DEBUG ANALYSIS COMPLETE")
    print("=" * 70)

async def test_websocket_simple():
    """Minimal WebSocket test"""
    print("Simple WebSocket test...")
    config = get_staging_config()
    headers = config.get_websocket_headers()
    
    try:
        async with websockets.connect(
            config.websocket_url,
            additional_headers=headers,
            close_timeout=5
        ) as ws:
            print("Connected!")
            # Just wait a bit and see what happens
            await asyncio.sleep(1)
            print("Still connected after 1 second")
            
    except Exception as e:
        print(f"Error: {e}")
        print(f"Type: {type(e)}")

if __name__ == "__main__":
    print("Choose test:")
    print("1. Full debug analysis")
    print("2. Simple connection test")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        asyncio.run(test_websocket_simple())
    else:
        asyncio.run(debug_websocket_connection())