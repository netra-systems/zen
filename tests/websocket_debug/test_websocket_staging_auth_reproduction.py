"""
WebSocket Staging Authentication Issue Reproduction Test

This test reproduces the exact WebSocket JWT 403 authentication failure happening in staging.
Following CLAUDE.md's MANDATORY BUG FIXING PROCESS - this test should FAIL before fix, PASS after fix.

CRITICAL: This test uses REAL staging services and REAL JWT tokens to reproduce the exact failure.
"""

import asyncio
import os
import sys
import time
import websockets
import httpx
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tests.e2e.staging_test_config import get_staging_config
from tests.e2e.jwt_token_helpers import JWTTestHelper


class WebSocketStagingAuthReproduction:
    """Reproduce the exact WebSocket authentication failure in staging."""
    
    def __init__(self):
        self.config = get_staging_config()
        self.jwt_helper = JWTTestHelper(environment="staging")
        
    async def test_websocket_auth_failure_reproduction(self) -> Dict[str, Any]:
        """
        Reproduce the exact WebSocket authentication failure.
        
        This test should FAIL with HTTP 403 before the fix is applied.
        """
        print("[REPRODUCING] WEBSOCKET STAGING AUTH FAILURE")
        print("=" * 60)
        
        results = {
            "test_name": "websocket_auth_failure_reproduction",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "staging_url": self.config.websocket_url,
            "steps": [],
            "success": False,
            "error_details": None
        }
        
        try:
            # STEP 1: Get staging JWT token using CURRENT method
            print("[U+1F4DD] STEP 1: Creating staging JWT token...")
            
            step1_result = {"step": "token_creation", "success": False}
            
            # This should reproduce the exact token creation that's currently failing
            token = await self.jwt_helper.get_staging_jwt_token(
                user_id="reproduction-test-user",
                email="reproduction-test@staging.netrasystems.ai"
            )
            
            if token:
                print(f" PASS:  JWT token created: {token[:20]}...")
                step1_result["success"] = True
                step1_result["token_length"] = len(token)
                step1_result["token_prefix"] = token[:20]
            else:
                print(" FAIL:  Failed to create JWT token")
                step1_result["error"] = "Token creation failed"
                results["steps"].append(step1_result)
                return results
                
            results["steps"].append(step1_result)
            
            # STEP 2: Test WebSocket connection with token
            print("[U+1F4DD] STEP 2: Testing WebSocket connection...")
            
            step2_result = {"step": "websocket_connection", "success": False}
            
            # This should reproduce the exact HTTP 403 failure
            websocket_url = f"{self.config.websocket_url}?token={token}"
            print(f"[U+1F517] Connecting to: {websocket_url}")
            
            try:
                # Timeout after 10 seconds to avoid hanging
                async with websockets.connect(
                    websocket_url,
                    timeout=10,
                    extra_headers={
                        "Authorization": f"Bearer {token}",
                        "User-Agent": "WebSocket-Auth-Reproduction-Test",
                        "Origin": "https://app.staging.netrasystems.ai"
                    }
                ) as websocket:
                    # If we get here, connection succeeded
                    await websocket.ping()
                    print(" PASS:  WebSocket connection successful!")
                    step2_result["success"] = True
                    step2_result["connection_state"] = "established"
                    results["success"] = True
                    
            except websockets.exceptions.ConnectionClosedError as e:
                # This is the expected failure
                print(f" FAIL:  WebSocket connection rejected: {e}")
                step2_result["error"] = f"Connection closed: {e.code} - {e.reason}"
                step2_result["close_code"] = e.code
                step2_result["close_reason"] = e.reason
                
                if e.code == 403 or "403" in str(e):
                    print("[REPRODUCED] HTTP 403 WebSocket authentication failure!")
                    step2_result["reproduced_issue"] = True
                    
            except websockets.exceptions.InvalidStatus as e:
                # Also expected for HTTP 403 responses
                print(f" FAIL:  WebSocket connection rejected with HTTP status: {e.status_code}")
                step2_result["error"] = f"HTTP {e.status_code}: {e.response.reason_phrase}"
                step2_result["http_status"] = e.status_code
                
                if e.status_code == 403:
                    print("[REPRODUCED] HTTP 403 WebSocket authentication failure!")
                    step2_result["reproduced_issue"] = True
                    
            except Exception as e:
                print(f" FAIL:  WebSocket connection failed: {e}")
                step2_result["error"] = str(e)
                
            results["steps"].append(step2_result)
            
            # STEP 3: Analyze JWT token structure  
            print("[U+1F4DD] STEP 3: Analyzing JWT token structure...")
            
            step3_result = {"step": "jwt_analysis", "success": False}
            
            try:
                import jwt
                
                # Decode without verification to see payload
                payload = jwt.decode(token, options={"verify_signature": False})
                
                print(" SEARCH:  JWT Token Payload:")
                for key, value in payload.items():
                    if key in ['exp', 'iat']:
                        # Convert timestamps to readable dates
                        readable_time = datetime.fromtimestamp(value, tz=timezone.utc)
                        print(f"  {key}: {value} ({readable_time})")
                    else:
                        print(f"  {key}: {value}")
                
                step3_result["success"] = True
                step3_result["payload"] = payload
                step3_result["user_id"] = payload.get("sub")
                step3_result["email"] = payload.get("email")
                step3_result["permissions"] = payload.get("permissions", [])
                
            except Exception as e:
                print(f" FAIL:  JWT analysis failed: {e}")
                step3_result["error"] = str(e)
                
            results["steps"].append(step3_result)
            
            # STEP 4: Test if user exists in staging database (if possible)
            print("[U+1F4DD] STEP 4: Testing staging user existence...")
            
            step4_result = {"step": "user_validation", "success": False}
            
            try:
                # Try to call staging backend API with the token
                async with httpx.AsyncClient(timeout=10) as client:
                    response = await client.get(
                        f"{self.config.backend_url}/api/users/me",
                        headers={"Authorization": f"Bearer {token}"}
                    )
                    
                    if response.status_code == 200:
                        user_data = response.json()
                        print(f" PASS:  User exists in staging: {user_data.get('email', 'unknown')}")
                        step4_result["success"] = True
                        step4_result["user_data"] = user_data
                    elif response.status_code == 401:
                        print(" FAIL:  JWT token invalid for staging backend API")
                        step4_result["error"] = "JWT token rejected by backend API"
                    elif response.status_code == 404:
                        print(" FAIL:  User does not exist in staging database")
                        step4_result["error"] = "User not found in staging database"
                    else:
                        print(f" FAIL:  Unexpected API response: {response.status_code}")
                        step4_result["error"] = f"HTTP {response.status_code}: {response.text}"
                        
            except Exception as e:
                print(f" FAIL:  User validation test failed: {e}")
                step4_result["error"] = str(e)
                
            results["steps"].append(step4_result)
            
        except Exception as e:
            print(f" FAIL:  Test execution failed: {e}")
            results["error_details"] = str(e)
            
        finally:
            print("\n" + "=" * 60)
            print(" SEARCH:  REPRODUCTION TEST SUMMARY")
            print("=" * 60)
            
            for step in results["steps"]:
                status = " PASS: " if step["success"] else " FAIL: "
                print(f"{status} {step['step']}: {'SUCCESS' if step['success'] else 'FAILED'}")
                if "error" in step:
                    print(f"   Error: {step['error']}")
                if "reproduced_issue" in step:
                    print(f"    TARGET:  Successfully reproduced the staging WebSocket auth issue!")
            
            if results["success"]:
                print("\n CELEBRATION:  TEST PASSED: WebSocket authentication is working!")
                print("   This means the bug has been FIXED.")
            else:
                print("\n FAIL:  TEST FAILED: WebSocket authentication is failing!")
                print("   This confirms the bug is still present.")
                
        return results


async def main():
    """Run the WebSocket staging authentication reproduction test."""
    reproducer = WebSocketStagingAuthReproduction()
    
    print("[CRITICAL] WebSocket Staging Authentication Issue Reproduction")
    print("=" * 60)
    print("This test reproduces the exact failure happening in staging.")
    print("Expected: FAIL with HTTP 403 (before fix)")
    print("Expected: PASS with successful connection (after fix)")
    print("=" * 60)
    
    results = await reproducer.test_websocket_auth_failure_reproduction()
    
    # Print final analysis
    print("\n[FINAL ANALYSIS]")
    print("=" * 60)
    
    if not results["success"]:
        print(" PASS:  BUG SUCCESSFULLY REPRODUCED")
        print("   - WebSocket connection fails with authentication error")
        print("   - This confirms the staging authentication issue exists")
        print("   - Ready to apply fix and retest")
    else:
        print(" FAIL:  BUG NOT REPRODUCED")
        print("   - WebSocket connection succeeded unexpectedly")
        print("   - Either bug is already fixed or test needs adjustment")
        
    print("\n[RESULTS] Test Results Summary:")
    for i, step in enumerate(results["steps"], 1):
        print(f"   Step {i} ({step['step']}): {'PASS' if step['success'] else 'FAIL'}")
        
    return results


if __name__ == "__main__":
    """
    Run this test to reproduce the WebSocket staging authentication issue.
    
    Usage:
        python test_websocket_staging_auth_reproduction.py
        
    Expected behavior:
    - BEFORE FIX: Test should FAIL with HTTP 403 WebSocket rejection
    - AFTER FIX: Test should PASS with successful WebSocket connection
    """
    import asyncio
    
    try:
        results = asyncio.run(main())
        
        # Exit with appropriate code for CI/CD pipeline
        if results["success"]:
            print("\n PASS:  Test completed successfully")
            sys.exit(0)  # Success - bug is fixed
        else:
            print("\n FAIL:  Test failed - bug reproduced")
            sys.exit(1)  # Failure - bug exists (expected before fix)
            
    except KeyboardInterrupt:
        print("\n[U+1F6D1] Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[CRASHED] Test crashed: {e}")
        sys.exit(2)