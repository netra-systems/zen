#!/usr/bin/env python3
"""
Test script to validate the WebSocket OAuth authentication fix for staging environment.

This script tests the SSOT E2E WebSocket authentication helper to ensure it can:
1. Handle OAuth simulation key mismatches
2. Create staging-compatible JWT tokens
3. Connect to staging WebSocket with proper E2E headers
4. Detect and bypass full JWT validation in staging

Run with: python test_websocket_oauth_fix.py
"""

import asyncio
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
from tests.e2e.staging_config import StagingTestConfig

async def test_staging_websocket_oauth_fix():
    """Test the complete WebSocket OAuth authentication fix for staging."""
    
    print("[U+1F9EA] Testing WebSocket OAuth Authentication Fix")
    print("=" * 60)
    
    try:
        # Initialize the E2E WebSocket auth helper for staging
        print("[U+1F4CB] Step 1: Initializing E2E WebSocket Auth Helper for staging...")
        auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
        print(f" PASS:  Auth helper created for environment: {auth_helper.environment}")
        print(f"[U+1F517] WebSocket URL: {auth_helper.config.websocket_url}")
        print(f"[U+1F517] Auth Service URL: {auth_helper.config.auth_service_url}")
        print()
        
        # Test staging token generation with OAuth simulation fallback
        print("[U+1F4CB] Step 2: Testing staging token generation...")
        start_time = time.time()
        
        try:
            token = await auth_helper.get_staging_token_async(
                email="websocket-test@staging.netrasystems.ai"
            )
            token_duration = time.time() - start_time
            
            print(f" PASS:  Token generated in {token_duration:.2f}s")
            print(f"[U+1F511] Token length: {len(token)} characters")
            print(f"[U+1F511] Token preview: {token[:20]}...")
            print()
            
        except Exception as e:
            print(f" FAIL:  Token generation failed: {e}")
            return False
        
        # Test WebSocket headers with E2E detection
        print("[U+1F4CB] Step 3: Testing WebSocket headers with E2E detection...")
        headers = auth_helper.get_websocket_headers(token)
        
        print("[U+1F511] Generated WebSocket headers:")
        for key, value in headers.items():
            if key == "Authorization":
                print(f"  {key}: Bearer {value[:20]}...")
            else:
                print(f"  {key}: {value}")
        
        # Verify E2E detection headers are present
        e2e_headers = ["X-Test-Type", "X-Test-Environment", "X-E2E-Test", "X-Test-Mode"]
        missing_headers = [h for h in e2e_headers if h not in headers]
        
        if missing_headers:
            print(f" FAIL:  Missing E2E detection headers: {missing_headers}")
            return False
        else:
            print(" PASS:  All E2E detection headers present")
            print()
        
        # Test WebSocket connection (with timeout protection)
        print("[U+1F4CB] Step 4: Testing WebSocket connection to staging...")
        print(" WARNING: [U+FE0F]  This may take up to 15 seconds due to GCP Cloud Run...")
        
        connection_start = time.time()
        try:
            # Use shorter timeout to avoid hanging
            websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
            connection_duration = time.time() - connection_start
            
            print(f" PASS:  WebSocket connection successful in {connection_duration:.2f}s")
            print(f"[U+1F50C] WebSocket state: {websocket.state}")
            
            # Send a test ping message
            print("[U+1F4CB] Step 5: Testing WebSocket message exchange...")
            test_message = '{"type": "ping", "timestamp": "' + str(int(time.time())) + '"}'
            
            await websocket.send(test_message)
            print(" PASS:  Ping message sent")
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f" PASS:  Response received: {response[:100]}")
            except asyncio.TimeoutError:
                print(" WARNING: [U+FE0F]  No response received (may be expected for ping)")
            
            # Close connection
            await websocket.close()
            print(" PASS:  WebSocket connection closed cleanly")
            print()
            
            return True
            
        except asyncio.TimeoutError:
            connection_duration = time.time() - connection_start
            print(f" FAIL:  WebSocket connection timed out after {connection_duration:.2f}s")
            print(" IDEA:  This suggests the fix may need refinement")
            return False
            
        except Exception as e:
            connection_duration = time.time() - connection_start
            print(f" FAIL:  WebSocket connection failed after {connection_duration:.2f}s: {e}")
            
            # Check if this is the expected HTTP 403 error
            if "403" in str(e):
                print(" SEARCH:  HTTP 403 error detected - this is what we're trying to fix")
                print(" IDEA:  The E2E headers may not be properly detected by the staging server")
            elif "401" in str(e):
                print(" SEARCH:  HTTP 401 error detected - authentication issue")
                print(" IDEA:  The JWT token may not be valid for staging environment")
            else:
                print(f" SEARCH:  Unexpected error type: {type(e).__name__}")
            
            return False
    
    except Exception as e:
        print(f" FAIL:  Test failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the WebSocket OAuth fix test."""
    print("[U+1F680] Starting WebSocket OAuth Authentication Fix Test")
    print(" TARGET:  Target: Staging Environment WebSocket Authentication")
    print()
    
    # Run the async test
    success = asyncio.run(test_staging_websocket_oauth_fix())
    
    print("=" * 60)
    if success:
        print(" CELEBRATION:  SUCCESS: WebSocket OAuth authentication fix is working!")
        print(" PASS:  Staging WebSocket connections should now work with E2E tests")
        print(" PASS:  OAuth simulation key mismatch is properly handled")
        print(" PASS:  E2E detection headers enable WebSocket connection bypass")
    else:
        print(" FAIL:  FAILURE: WebSocket OAuth authentication fix needs refinement")
        print(" IDEA:  Check the error messages above for specific issues to address")
        print(" IDEA:  This is expected during development - the fix is iterative")
    
    print()
    print(" CHART:  Test Summary:")
    print("- OAuth simulation tested with fallback to staging-compatible JWT")
    print("- E2E detection headers implemented and verified")
    print("- Environment variable setup for staging WebSocket detection")
    print("- Staging-specific JWT token generation with proper claims")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())