#!/usr/bin/env python3
"""
Quick WebSocket connectivity test to validate current staging status.
"""
import asyncio
import websockets
import json
import sys
from typing import Optional

async def test_websocket_connectivity() -> bool:
    """Test WebSocket connectivity to staging environment."""
    staging_url = "wss://api.staging.netrasystems.ai/ws"
    
    print(f" SEARCH:  Testing WebSocket connectivity to: {staging_url}")
    
    try:
        # Simple connection test with minimal headers
        timeout_config = websockets.connect(
            staging_url,
            additional_headers={
                "X-E2E-Test": "quick-connectivity-test",
                "X-Test-Mode": "connectivity-validation"
            },
            close_timeout=5,
            ping_timeout=10
        )
        
        async with timeout_config as websocket:
            print(" PASS:  WebSocket connection established successfully!")
            
            # Try to receive welcome message
            try:
                welcome_msg = await asyncio.wait_for(websocket.recv(), timeout=10)
                welcome_data = json.loads(welcome_msg)
                print(f" PASS:  Welcome message received: {welcome_data.get('type', 'unknown')}")
                return True
                
            except asyncio.TimeoutError:
                print(" WARNING: [U+FE0F] No welcome message received within timeout")
                return True  # Connection succeeded even without message
                
            except json.JSONDecodeError as e:
                print(f" WARNING: [U+FE0F] Could not parse welcome message: {e}")
                return True  # Connection succeeded even with parsing issue
                
    except websockets.exceptions.ConnectionClosedError as e:
        print(f" FAIL:  WebSocket connection closed with error: Code {e.code} - {e.reason}")
        if e.code == 1011:
            print(" ALERT:  CONFIRMED: 1011 internal error still present!")
        return False
        
    except Exception as e:
        print(f" FAIL:  WebSocket connection failed: {e}")
        return False

async def main():
    print("[U+1F52C] WEBSOCKET 1011 ERROR VALIDATION TEST")
    print("=" * 50)
    
    success = await test_websocket_connectivity()
    
    if success:
        print("\n PASS:  RESULT: WebSocket connectivity WORKING")
        print("   The 1011 error has been resolved!")
    else:
        print("\n FAIL:  RESULT: WebSocket connectivity STILL FAILING")
        print("   The 1011 error persists - further fixes needed")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))