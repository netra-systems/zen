"""
WebSocket Connection Timeout Reproduction Test
Reproduces the exact "connection_established" timeout issue from staging.
Business Impact: $120K+ MRR at risk - core chat functionality broken
"""

import asyncio
import json
import time
import websockets
from datetime import datetime
from typing import Optional

from tests.e2e.staging_test_config import get_staging_config
from tests.helpers.auth_test_utils import TestAuthHelper


async def test_websocket_connection_established_timeout():
    """
    Reproduction test for WebSocket connection_established message timeout.
    
    This test reproduces the exact issue where:
    1. WebSocket connection is established successfully
    2. Client waits for "connection_established" welcome message
    3. Message never arrives, causing asyncio.TimeoutError after 10s
    """
    print("🚨 WebSocket Connection Timeout Reproduction Test")
    print("=" * 60)
    
    config = get_staging_config()
    auth_helper = TestAuthHelper(environment="staging")
    
    # Create test token for authentication
    test_token = auth_helper.create_test_token(
        f"websocket_timeout_test_{int(time.time())}", 
        "timeout_test@netrasystems.ai"
    )
    
    start_time = time.time()
    connection_established = False
    welcome_message_received = False
    timeout_occurred = False
    
    print(f"[INFO] Target WebSocket URL: {config.websocket_url}")
    print(f"[INFO] Using JWT token: {test_token[:20]}...")
    
    try:
        # Attempt WebSocket connection with authentication
        headers = {"Authorization": f"Bearer {test_token}"}
        
        async with websockets.connect(
            config.websocket_url,
            additional_headers=headers,
            close_timeout=10
        ) as ws:
            connection_established = True
            print(f"✅ WebSocket connection established at {datetime.now().isoformat()}")
            
            # This is the critical test - wait for connection_established message
            print("🔍 Waiting for 'connection_established' welcome message...")
            print("   Expected message format: {\"event\": \"connection_established\", \"connection_ready\": true}")
            print("   Timeout: 10 seconds")
            
            try:
                # This should receive the welcome message from websocket.py line 571-588
                welcome_response = await asyncio.wait_for(ws.recv(), timeout=10.0)
                welcome_message_received = True
                
                print(f"✅ Welcome message received: {welcome_response}")
                
                # Parse and validate message format
                try:
                    welcome_data = json.loads(welcome_response)
                    
                    if welcome_data.get("event") == "connection_established":
                        print("✅ Correct message type: connection_established")
                        
                        if welcome_data.get("connection_ready"):
                            print("✅ Connection ready flag present")
                        else:
                            print("⚠️ Connection ready flag missing")
                            
                        if welcome_data.get("connection_id"):
                            print(f"✅ Connection ID: {welcome_data['connection_id']}")
                        else:
                            print("⚠️ Connection ID missing")
                            
                    else:
                        print(f"❌ Unexpected message type: {welcome_data.get('event')}")
                        
                except json.JSONDecodeError as e:
                    print(f"❌ Welcome message is not valid JSON: {e}")
                    
            except asyncio.TimeoutError:
                timeout_occurred = True
                print("❌ TIMEOUT: No welcome message received within 10 seconds")
                print("   This confirms the bug - connection_established message not sent")
                
    except websockets.exceptions.InvalidStatus as e:
        # Handle authentication errors
        status_code = getattr(e, 'status_code', 0)
        
        if status_code in [401, 403]:
            print(f"❌ Authentication failed: {e}")
            print("   This indicates JWT token or auth service issues")
        else:
            print(f"❌ WebSocket connection failed: {e}")
            raise
            
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        raise
        
    finally:
        duration = time.time() - start_time
        print("\n" + "=" * 60)
        print("📊 Test Results Summary")
        print("=" * 60)
        print(f"Test Duration: {duration:.3f}s")
        print(f"Connection Established: {'✅ YES' if connection_established else '❌ NO'}")
        print(f"Welcome Message Received: {'✅ YES' if welcome_message_received else '❌ NO'}")
        print(f"Timeout Occurred: {'❌ YES' if timeout_occurred else '✅ NO'}")
        
        if connection_established and not welcome_message_received:
            print("\n🔍 DIAGNOSIS:")
            print("   - WebSocket connection succeeds (authentication working)")
            print("   - Welcome message never arrives (server-side issue)")
            print("   - Likely causes:")
            print("     1. SSOT authentication failing after connection acceptance")
            print("     2. Service dependencies (agent_supervisor/thread_service) missing")
            print("     3. Startup sequence hanging or failing")
            print("     4. Code execution never reaches welcome message logic")
            
        if timeout_occurred:
            print("\n🚨 BUG CONFIRMED:")
            print("   This reproduces the exact issue from test_001_websocket_connection_real")
            print("   The WebSocket server is not sending the expected welcome message")
            
        # Verify this was a real test
        assert duration > 0.1, f"Test too fast ({duration:.3f}s) - likely fake"
        
        # The bug is confirmed if we have connection but no welcome message
        bug_reproduced = connection_established and not welcome_message_received and timeout_occurred
        
        if bug_reproduced:
            print("\n✅ BUG SUCCESSFULLY REPRODUCED")
            print("   Ready for root cause fix implementation")
        else:
            print("\n❓ Bug not reproduced - may be intermittent or already fixed")
            
        return {
            "bug_reproduced": bug_reproduced,
            "connection_established": connection_established,
            "welcome_message_received": welcome_message_received,
            "timeout_occurred": timeout_occurred,
            "duration": duration
        }


if __name__ == "__main__":
    print("Starting WebSocket timeout reproduction test...")
    result = asyncio.run(test_websocket_connection_established_timeout())
    
    if result["bug_reproduced"]:
        print("\n🔧 NEXT STEPS:")
        print("1. Examine WebSocket endpoint authentication flow")
        print("2. Check service dependencies in staging environment")  
        print("3. Add comprehensive logging to WebSocket handler")
        print("4. Implement SSOT-compliant fix")
        exit(1)  # Exit with error to indicate bug confirmed
    else:
        print("\n✅ No timeout issue detected")
        exit(0)