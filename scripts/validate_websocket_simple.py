#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple WebSocket Deployment Validation Script
Windows-compatible version without Unicode characters
"""

import asyncio
import json
import sys
import time
import os
from typing import Dict, Optional, List, Tuple
from datetime import datetime

# Windows encoding fix
if sys.platform == "win32":
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Try to import websockets
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("WARNING: websockets library not available. Install with: pip install websockets")

class SimpleWebSocketValidator:
    """Simple WebSocket validation for staging deployment."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.base_urls = self._get_environment_urls()
    
    def _get_environment_urls(self) -> Dict[str, str]:
        """Get environment-specific URLs."""
        if self.environment == "staging":
            return {
                "api": "https://api.staging.netrasystems.ai",
                "frontend": "https://app.staging.netrasystems.ai"
            }
        elif self.environment == "production":
            return {
                "api": "https://api.netrasystems.ai",
                "frontend": "https://app.netrasystems.ai"
            }
        else:
            raise ValueError(f"Unknown environment: {self.environment}")
    
    async def test_websocket_connection(self) -> Tuple[bool, str]:
        """Test basic WebSocket connection."""
        if not WEBSOCKETS_AVAILABLE:
            return False, "websockets library not available"
        
        # Test multiple endpoints
        endpoints = ["/ws/test", "/ws", "/websocket"]
        
        for endpoint in endpoints:
            ws_url = self.base_urls["api"].replace("https://", "wss://") + endpoint
            
            try:
                print(f"Testing: {ws_url}")
                
                async with websockets.connect(
                    ws_url,
                    timeout=10,
                    extra_headers={
                        "Origin": self.base_urls["frontend"],
                        "User-Agent": "SimpleWebSocketValidator/1.0"
                    }
                ) as websocket:
                    
                    # Send test message
                    test_msg = {"type": "ping", "timestamp": time.time()}
                    await websocket.send(json.dumps(test_msg))
                    
                    # Try to get response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        print(f"  SUCCESS: Got response on {endpoint}")
                        return True, f"Connected successfully to {endpoint}"
                    except asyncio.TimeoutError:
                        print(f"  SUCCESS: Connected to {endpoint} (no response)")
                        return True, f"Connected to {endpoint} (timeout on response)"
                        
            except Exception as e:
                print(f"  FAILED: {endpoint} - {e}")
                continue
        
        return False, "All endpoints failed"
    
    async def test_websocket_timeout(self) -> Tuple[bool, str]:
        """Test that WebSocket connections can last longer than 30 seconds."""
        if not WEBSOCKETS_AVAILABLE:
            return False, "websockets library not available"
        
        ws_url = self.base_urls["api"].replace("https://", "wss://") + "/ws/test"
        
        try:
            print(f"Testing timeout: {ws_url}")
            
            start_time = time.time()
            async with websockets.connect(
                ws_url,
                timeout=15,
                extra_headers={"Origin": self.base_urls["frontend"]}
            ) as websocket:
                
                # Keep connection alive for 40 seconds
                for i in range(8):  # 8 * 5 = 40 seconds
                    await asyncio.sleep(5)
                    elapsed = time.time() - start_time
                    print(f"  Connection alive at {elapsed:.1f}s")
                    
                    try:
                        await websocket.send(json.dumps({"type": "ping", "seq": i}))
                    except Exception as e:
                        if elapsed > 35:
                            print(f"  SUCCESS: Connection lasted {elapsed:.1f}s")
                            return True, f"Connection lasted {elapsed:.1f}s (timeout fixed)"
                        else:
                            return False, f"Connection failed at {elapsed:.1f}s: {e}"
                
                elapsed = time.time() - start_time
                print(f"  SUCCESS: Full test completed at {elapsed:.1f}s")
                return True, f"Connection stable for {elapsed:.1f}s"
                
        except Exception as e:
            return False, f"Timeout test failed: {e}"
    
    async def run_validation(self) -> bool:
        """Run WebSocket validation tests."""
        print(f"\n=== WebSocket Validation - {self.environment.upper()} ===")
        
        if not WEBSOCKETS_AVAILABLE:
            print("ERROR: websockets library not available")
            return False
        
        results = []
        
        # Test 1: Basic connection
        print("\n1. Testing WebSocket Connection...")
        success, message = await self.test_websocket_connection()
        results.append(("Connection Test", success, message))
        print(f"   Result: {'PASS' if success else 'FAIL'} - {message}")
        
        # Test 2: Timeout test (only if basic connection works)
        if success:
            print("\n2. Testing WebSocket Timeout...")
            success, message = await self.test_websocket_timeout()
            results.append(("Timeout Test", success, message))
            print(f"   Result: {'PASS' if success else 'FAIL'} - {message}")
        
        # Summary
        print(f"\n=== SUMMARY ===")
        all_passed = True
        for test_name, passed, message in results:
            status = "PASS" if passed else "FAIL"
            print(f"{test_name}: {status}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\nOVERALL: SUCCESS - WebSocket deployment ready")
        else:
            print("\nOVERALL: FAILED - Issues detected")
        
        return all_passed

async def main():
    """Main entry point."""
    environment = sys.argv[1] if len(sys.argv) > 1 else "staging"
    
    try:
        validator = SimpleWebSocketValidator(environment)
        success = await validator.run_validation()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"Validation error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())