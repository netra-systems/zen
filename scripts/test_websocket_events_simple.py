#!/usr/bin/env python3
"""
Simple WebSocket Authentication Test
Tests WebSocket connection to staging environment to diagnose auth failures.
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper, E2EAuthConfig


async def test_staging_websocket_auth():
    """Test WebSocket authentication in staging environment."""
    
    print("=== Simple WebSocket Authentication Test ===")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    
    # Create staging configuration
    config = E2EAuthConfig.for_staging()
    print(f"WebSocket URL: {config.websocket_url}")
    
    # Create WebSocket auth helper
    auth_helper = E2EWebSocketAuthHelper(config=config, environment="staging")
    
    print("\n1. Creating staging-compatible JWT token...")
    try:
        # Create staging token 
        token = await auth_helper.get_staging_token_async(
            email="staging-e2e-user-002@netrasystems.ai"
        )
        print(f" PASS:  Token created successfully")
        print(f"Token (first 50 chars): {token[:50]}...")
    except Exception as e:
        print(f" FAIL:  Token creation failed: {e}")
        return False
    
    print("\n2. Getting WebSocket headers with E2E detection...")
    headers = auth_helper.get_websocket_headers(token)
    print(f"Headers: {list(headers.keys())}")
    for key, value in headers.items():
        if key.lower() == 'authorization':
            print(f"  {key}: Bearer {value[7:57]}...")  # Show first 50 chars of token
        else:
            print(f"  {key}: {value}")
    
    print("\n3. Attempting WebSocket connection...")
    try:
        import websockets
        
        start_time = time.time()
        
        # Try to connect with authentication
        async with websockets.connect(
            config.websocket_url,
            additional_headers=headers,
            open_timeout=10.0,
            close_timeout=5.0
        ) as websocket:
            connection_time = time.time() - start_time
            print(f" PASS:  WebSocket connected successfully in {connection_time:.2f}s")
            
            # Send a simple message
            test_message = {
                "type": "ping",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "test": "staging_auth"
            }
            
            print("\n4. Sending test message...")
            await websocket.send(json.dumps(test_message))
            print(" PASS:  Message sent")
            
            # Wait for response
            print("\n5. Waiting for response...")
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f" PASS:  Received response: {response}")
                
                # Parse and display response
                try:
                    response_data = json.loads(response)
                    print(f"Response type: {response_data.get('type')}")
                    print(f"Response event: {response_data.get('event', 'N/A')}")
                except json.JSONDecodeError:
                    print("Response is not JSON")
                    
            except asyncio.TimeoutError:
                print(" WARNING: [U+FE0F]  No response received (timeout)")
                
            print(f" PASS:  Test completed successfully")
            return True
            
    except Exception as e:
        connection_time = time.time() - start_time
        print(f" FAIL:  WebSocket connection failed after {connection_time:.2f}s: {e}")
        
        # Enhanced error analysis
        error_str = str(e).lower()
        if "1008" in error_str:
            print(" SEARCH:  Error Analysis: 1008 = Policy Violation (likely authentication failure)")
            print("   This indicates the server rejected the connection due to authentication")
        elif "timeout" in error_str:
            print(" SEARCH:  Error Analysis: Connection timeout")
            print("   This may indicate server is not responding or taking too long to process auth")
        elif "403" in error_str:
            print(" SEARCH:  Error Analysis: 403 Forbidden")
            print("   This indicates authentication was rejected")
        elif "401" in error_str:
            print(" SEARCH:  Error Analysis: 401 Unauthorized")
            print("   This indicates no valid authentication was provided")
        else:
            print(f" SEARCH:  Error Analysis: Unknown error pattern")
            
        return False


if __name__ == "__main__":
    result = asyncio.run(test_staging_websocket_auth())
    sys.exit(0 if result else 1)