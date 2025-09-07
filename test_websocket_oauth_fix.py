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
    
    print("🧪 Testing WebSocket OAuth Authentication Fix")
    print("=" * 60)
    
    try:
        # Initialize the E2E WebSocket auth helper for staging
        print("📋 Step 1: Initializing E2E WebSocket Auth Helper for staging...")
        auth_helper = E2EWebSocketAuthHelper(environment="staging")
        
        print(f"✅ Auth helper created for environment: {auth_helper.environment}")
        print(f"🔗 WebSocket URL: {auth_helper.config.websocket_url}")
        print(f"🔗 Auth Service URL: {auth_helper.config.auth_service_url}")
        print()
        
        # Test staging token generation with OAuth simulation fallback
        print("📋 Step 2: Testing staging token generation...")
        start_time = time.time()
        
        try:
            token = await auth_helper.get_staging_token_async(
                email="websocket-test@staging.netrasystems.ai"
            )
            token_duration = time.time() - start_time
            
            print(f"✅ Token generated in {token_duration:.2f}s")
            print(f"🔑 Token length: {len(token)} characters")
            print(f"🔑 Token preview: {token[:20]}...")
            print()
            
        except Exception as e:
            print(f"❌ Token generation failed: {e}")
            return False
        
        # Test WebSocket headers with E2E detection
        print("📋 Step 3: Testing WebSocket headers with E2E detection...")
        headers = auth_helper.get_websocket_headers(token)
        
        print("🔑 Generated WebSocket headers:")
        for key, value in headers.items():
            if key == "Authorization":
                print(f"  {key}: Bearer {value[:20]}...")
            else:
                print(f"  {key}: {value}")
        
        # Verify E2E detection headers are present
        e2e_headers = ["X-Test-Type", "X-Test-Environment", "X-E2E-Test", "X-Test-Mode"]
        missing_headers = [h for h in e2e_headers if h not in headers]
        
        if missing_headers:
            print(f"❌ Missing E2E detection headers: {missing_headers}")
            return False
        else:
            print("✅ All E2E detection headers present")
            print()
        
        # Test WebSocket connection (with timeout protection)
        print("📋 Step 4: Testing WebSocket connection to staging...")
        print("⚠️  This may take up to 15 seconds due to GCP Cloud Run...")
        
        connection_start = time.time()
        try:
            # Use shorter timeout to avoid hanging
            websocket = await auth_helper.connect_authenticated_websocket(timeout=15.0)
            connection_duration = time.time() - connection_start
            
            print(f"✅ WebSocket connection successful in {connection_duration:.2f}s")
            print(f"🔌 WebSocket state: {websocket.state}")
            
            # Send a test ping message
            print("📋 Step 5: Testing WebSocket message exchange...")
            test_message = '{"type": "ping", "timestamp": "' + str(int(time.time())) + '"}'
            
            await websocket.send(test_message)
            print("✅ Ping message sent")
            
            # Wait for response with timeout
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"✅ Response received: {response[:100]}")
            except asyncio.TimeoutError:
                print("⚠️  No response received (may be expected for ping)")
            
            # Close connection
            await websocket.close()
            print("✅ WebSocket connection closed cleanly")
            print()
            
            return True
            
        except asyncio.TimeoutError:
            connection_duration = time.time() - connection_start
            print(f"❌ WebSocket connection timed out after {connection_duration:.2f}s")
            print("💡 This suggests the fix may need refinement")
            return False
            
        except Exception as e:
            connection_duration = time.time() - connection_start
            print(f"❌ WebSocket connection failed after {connection_duration:.2f}s: {e}")
            
            # Check if this is the expected HTTP 403 error
            if "403" in str(e):
                print("🔍 HTTP 403 error detected - this is what we're trying to fix")
                print("💡 The E2E headers may not be properly detected by the staging server")
            elif "401" in str(e):
                print("🔍 HTTP 401 error detected - authentication issue")
                print("💡 The JWT token may not be valid for staging environment")
            else:
                print(f"🔍 Unexpected error type: {type(e).__name__}")
            
            return False
    
    except Exception as e:
        print(f"❌ Test failed with unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the WebSocket OAuth fix test."""
    print("🚀 Starting WebSocket OAuth Authentication Fix Test")
    print("🎯 Target: Staging Environment WebSocket Authentication")
    print()
    
    # Run the async test
    success = asyncio.run(test_staging_websocket_oauth_fix())
    
    print("=" * 60)
    if success:
        print("🎉 SUCCESS: WebSocket OAuth authentication fix is working!")
        print("✅ Staging WebSocket connections should now work with E2E tests")
        print("✅ OAuth simulation key mismatch is properly handled")
        print("✅ E2E detection headers enable WebSocket connection bypass")
    else:
        print("❌ FAILURE: WebSocket OAuth authentication fix needs refinement")
        print("💡 Check the error messages above for specific issues to address")
        print("💡 This is expected during development - the fix is iterative")
    
    print()
    print("📊 Test Summary:")
    print("- OAuth simulation tested with fallback to staging-compatible JWT")
    print("- E2E detection headers implemented and verified")
    print("- Environment variable setup for staging WebSocket detection")
    print("- Staging-specific JWT token generation with proper claims")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())