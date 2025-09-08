"""
Simple WebSocket Staging Authentication Test

This test reproduces the WebSocket JWT 403 authentication failure happening in staging.
Uses plain ASCII characters to avoid Windows Unicode issues.
"""

import asyncio
import os
import sys
import websockets
from datetime import datetime, timezone

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.e2e.staging_test_config import get_staging_config
from tests.e2e.jwt_token_helpers import JWTTestHelper


async def test_websocket_auth():
    """Test WebSocket authentication against staging."""
    
    print("WEBSOCKET STAGING AUTH TEST")
    print("=" * 50)
    
    config = get_staging_config()
    jwt_helper = JWTTestHelper(environment="staging")
    
    try:
        # Step 1: Create JWT token
        print("[STEP 1] Creating staging JWT token...")
        token = await jwt_helper.get_staging_jwt_token(
            user_id="test-ws-auth-user",
            email="test-ws-auth@staging.netrasystems.ai"
        )
        
        if not token:
            print("[FAILED] Could not create JWT token")
            return False
            
        print(f"[SUCCESS] Token created: {token[:20]}...")
        
        # Step 2: Test WebSocket connection
        print("[STEP 2] Testing WebSocket connection...")
        websocket_url = f"{config.websocket_url}?token={token}"
        print(f"[CONNECTING] URL: {websocket_url}")
        
        try:
            async with websockets.connect(
                websocket_url,
                timeout=10,
                extra_headers={
                    "Authorization": f"Bearer {token}",
                    "User-Agent": "Test-Client",
                    "Origin": "https://app.staging.netrasystems.ai"
                }
            ) as websocket:
                await websocket.ping()
                print("[SUCCESS] WebSocket connection established!")
                return True
                
        except websockets.exceptions.ConnectionClosedError as e:
            print(f"[FAILED] Connection rejected: {e}")
            if e.code == 403 or "403" in str(e):
                print("[REPRODUCED] HTTP 403 authentication failure!")
                return False
            return False
            
        except websockets.exceptions.InvalidStatusCode as e:
            print(f"[FAILED] HTTP Status: {e.status_code}")
            if e.status_code == 403:
                print("[REPRODUCED] HTTP 403 authentication failure!")
                return False
            return False
            
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            return False
            
    except Exception as e:
        print(f"[ERROR] Test failed: {e}")
        return False


async def main():
    """Run the test."""
    print("WebSocket Staging Authentication Test")
    print("Expected: FAIL with 403 (bug exists)")
    print("Expected: PASS (bug fixed)")
    print("-" * 50)
    
    success = await test_websocket_auth()
    
    print("\nFINAL RESULT:")
    if success:
        print("[PASS] WebSocket authentication working")
        print("This means the bug is FIXED")
        return 0
    else:
        print("[FAIL] WebSocket authentication failing")
        print("This confirms the bug EXISTS (expected before fix)")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Test stopped")
        sys.exit(130)
    except Exception as e:
        print(f"\n[CRASHED] Test error: {e}")
        sys.exit(2)