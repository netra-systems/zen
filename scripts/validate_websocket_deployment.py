#!/usr/bin/env python3
"""
WebSocket Deployment Validation Script
Validates WebSocket connectivity after GCP deployment.

CRITICAL: This script validates WebSocket infrastructure for $180K+ MRR chat functionality.
"""

import asyncio
import json
import sys
import time
from typing import Dict, Optional, List, Tuple
from datetime import datetime
import logging

# Try to import websockets - graceful fallback if not available
try:
    import websockets
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    print("WARNING: websockets library not available. Install with: pip install websockets")

class WebSocketDeploymentValidator:
    """Validates WebSocket connectivity in deployed environments."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.base_urls = self._get_environment_urls()
        self.results: List[Tuple[str, bool, str]] = []
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
    
    def _get_environment_urls(self) -> Dict[str, str]:
        """Get environment-specific URLs."""
        if self.environment == "staging":
            return {
                "api": "https://api.staging.netrasystems.ai",
                "auth": "https://auth.staging.netrasystems.ai",
                "frontend": "https://app.staging.netrasystems.ai"
            }
        elif self.environment == "production":
            return {
                "api": "https://api.netrasystems.ai",
                "auth": "https://auth.netrasystems.ai", 
                "frontend": "https://app.netrasystems.ai"
            }
        else:
            raise ValueError(f"Unknown environment: {self.environment}")
    
    async def validate_websocket_handshake(self) -> Tuple[bool, str]:
        """Test WebSocket handshake without authentication."""
        if not WEBSOCKETS_AVAILABLE:
            return False, "websockets library not available"
            
        # Try multiple WebSocket endpoints
        test_endpoints = [
            "/ws/test",
            "/ws",
            "/websocket"
        ]
        
        for endpoint in test_endpoints:
            ws_url = self.base_urls["api"].replace("https://", "wss://") + endpoint
            
            try:
                self.logger.info(f"Testing WebSocket handshake: {ws_url}")
                
                async with websockets.connect(
                    ws_url,
                    timeout=10,
                    extra_headers={
                        "Origin": self.base_urls["frontend"],
                        "User-Agent": "WebSocketDeploymentValidator/1.0",
                        "Connection": "Upgrade",
                        "Upgrade": "websocket"
                    }
                ) as websocket:
                    
                    # Send test message
                    test_msg = {
                        "type": "ping",
                        "timestamp": time.time(),
                        "test_id": f"deployment_validation_{int(time.time())}"
                    }
                    await websocket.send(json.dumps(test_msg))
                    
                    # Wait for response
                    try:
                        response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                        response_data = json.loads(response)
                        
                        if response_data.get("type") in ["connection_established", "pong", "error"]:
                            self.logger.info(f"✅ WebSocket handshake successful on {endpoint}")
                            return True, f"Successful handshake on {endpoint}"
                        else:
                            self.logger.info(f"⚠️ Unexpected response on {endpoint}: {response_data}")
                            continue
                    except asyncio.TimeoutError:
                        self.logger.info(f"⚠️ No response on {endpoint}, but connection established")
                        return True, f"Connection established on {endpoint} (no response timeout)"
                        
            except websockets.exceptions.WebSocketException as e:
                self.logger.info(f"❌ WebSocket protocol error on {endpoint}: {e}")
                continue
            except asyncio.TimeoutError:
                self.logger.info(f"❌ WebSocket connection timeout on {endpoint}")
                continue
            except Exception as e:
                self.logger.info(f"❌ WebSocket connection error on {endpoint}: {e}")
                continue
        
        return False, "All WebSocket endpoints failed"
    
    async def validate_websocket_with_auth(self) -> Tuple[bool, str]:
        """Test WebSocket with authentication behavior."""
        if not WEBSOCKETS_AVAILABLE:
            return False, "websockets library not available"
            
        ws_url = self.base_urls["api"].replace("https://", "wss://") + "/ws"
        
        try:
            self.logger.info(f"Testing authenticated WebSocket: {ws_url}")
            
            # Test without authentication - should get proper auth error
            async with websockets.connect(
                ws_url,
                timeout=10,
                extra_headers={
                    "Origin": self.base_urls["frontend"]
                }
            ) as websocket:
                
                try:
                    # Send message without auth
                    test_msg = {"type": "ping"}
                    await websocket.send(json.dumps(test_msg))
                    
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    response_data = json.loads(response)
                    
                    if "error" in response_data and "auth" in response_data.get("error", "").lower():
                        self.logger.info(f"✅ Authentication properly required")
                        return True, "Authentication properly enforced"
                    else:
                        self.logger.info(f"⚠️ Expected auth error but got: {response_data}")
                        return False, f"Authentication not enforced: {response_data}"
                        
                except websockets.exceptions.ConnectionClosedError as e:
                    if e.code == 1008:  # Authentication required
                        self.logger.info(f"✅ Authentication properly required (code 1008)")
                        return True, "Authentication enforced with proper close code"
                    else:
                        self.logger.info(f"⚠️ Unexpected close code: {e.code}")
                        return False, f"Unexpected close code: {e.code}"
                except asyncio.TimeoutError:
                    self.logger.info(f"⚠️ No auth response - connection might be working but no auth enforcement")
                    return False, "No authentication enforcement detected"
                        
        except Exception as e:
            self.logger.info(f"❌ Auth WebSocket test error: {e}")
            return False, f"Auth test error: {e}"
    
    async def validate_websocket_headers(self) -> Tuple[bool, str]:
        """Validate that proper WebSocket headers are handled."""
        if not WEBSOCKETS_AVAILABLE:
            return False, "websockets library not available"
        
        ws_url = self.base_urls["api"].replace("https://", "wss://") + "/ws"
        
        try:
            self.logger.info(f"Testing WebSocket headers: {ws_url}")
            
            # Test with explicit WebSocket headers
            headers = {
                "Origin": self.base_urls["frontend"],
                "Connection": "Upgrade",
                "Upgrade": "websocket",
                "Sec-WebSocket-Version": "13",
                "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ=="
            }
            
            async with websockets.connect(
                ws_url,
                timeout=10,
                extra_headers=headers
            ) as websocket:
                self.logger.info(f"✅ WebSocket headers properly handled")
                return True, "WebSocket headers properly handled"
                
        except websockets.exceptions.InvalidHandshake as e:
            self.logger.info(f"❌ WebSocket handshake failed: {e}")
            return False, f"Invalid handshake: {e}"
        except Exception as e:
            self.logger.info(f"❌ Header test error: {e}")
            return False, f"Header test error: {e}"
    
    async def validate_load_balancer_timeout(self) -> Tuple[bool, str]:
        """Validate load balancer timeout configuration."""
        if not WEBSOCKETS_AVAILABLE:
            return False, "websockets library not available"
            
        ws_url = self.base_urls["api"].replace("https://", "wss://") + "/ws/test"
        
        try:
            self.logger.info(f"Testing load balancer timeout: {ws_url}")
            
            start_time = time.time()
            async with websockets.connect(
                ws_url,
                timeout=15,
                extra_headers={"Origin": self.base_urls["frontend"]}
            ) as websocket:
                
                # Keep connection alive for 45 seconds (over old 30s timeout)
                for i in range(9):  # 9 * 5 = 45 seconds
                    await asyncio.sleep(5)
                    try:
                        ping_msg = {"type": "ping", "sequence": i}
                        await websocket.send(json.dumps(ping_msg))
                        
                        # Try to receive pong (optional)
                        try:
                            response = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                            self.logger.info(f"  Ping {i}: Response received")
                        except asyncio.TimeoutError:
                            self.logger.info(f"  Ping {i}: No response (connection still alive)")
                            
                    except Exception as e:
                        elapsed = time.time() - start_time
                        if elapsed < 35:  # Failed before expected timeout
                            self.logger.info(f"❌ Connection failed after {elapsed:.1f}s: {e}")
                            return False, f"Connection failed after {elapsed:.1f}s"
                        else:
                            self.logger.info(f"⚠️ Connection closed after {elapsed:.1f}s (expected)")
                            break
                
                elapsed = time.time() - start_time
                if elapsed >= 40:  # Successfully lasted longer than old timeout
                    self.logger.info(f"✅ Connection lasted {elapsed:.1f}s (load balancer timeout fixed)")
                    return True, f"Load balancer timeout fixed - connection lasted {elapsed:.1f}s"
                else:
                    return False, f"Connection only lasted {elapsed:.1f}s"
                    
        except Exception as e:
            self.logger.info(f"❌ Timeout test error: {e}")
            return False, f"Timeout test error: {e}"
    
    async def run_validation(self) -> bool:
        """Run complete WebSocket validation."""
        print(f"\n🔌 WebSocket Deployment Validation - {self.environment.upper()}")
        print("=" * 80)
        
        if not WEBSOCKETS_AVAILABLE:
            print("❌ CRITICAL: websockets library not available")
            print("Install with: pip install websockets")
            return False
        
        # Test 1: Basic handshake
        success, message = await self.validate_websocket_handshake()
        self.results.append(("WebSocket Handshake", success, message))
        
        # Test 2: Authentication behavior
        success, message = await self.validate_websocket_with_auth()
        self.results.append(("WebSocket Authentication", success, message))
        
        # Test 3: Header handling
        success, message = await self.validate_websocket_headers()
        self.results.append(("WebSocket Headers", success, message))
        
        # Test 4: Load balancer timeout
        success, message = await self.validate_load_balancer_timeout()
        self.results.append(("Load Balancer Timeout", success, message))
        
        # Print results
        print("\n📊 Validation Results:")
        print("-" * 80)
        all_passed = True
        critical_failed = False
        
        for test_name, passed, message in self.results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {test_name:.<30} {status}")
            print(f"    └─ {message}")
            
            if not passed:
                all_passed = False
                if "handshake" in test_name.lower() or "timeout" in test_name.lower():
                    critical_failed = True
        
        # Overall assessment
        print("\n" + "=" * 80)
        if all_passed:
            print("🎉 ALL WebSocket validation tests PASSED")
            print("✅ WebSocket deployment is ready for production traffic")
            print("✅ $180K+ MRR chat functionality infrastructure verified")
        elif critical_failed:
            print("🚨 CRITICAL WebSocket validation FAILED")
            print("❌ DO NOT proceed with production deployment")
            print("❌ Chat functionality at risk - $180K+ MRR impact")
        else:
            print("⚠️  WebSocket validation PARTIALLY PASSED")
            print("⚠️  Minor issues detected - review before production")
            print("✅ Basic functionality should work")
        
        print(f"\nValidation completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return all_passed

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="WebSocket Deployment Validation")
    parser.add_argument("environment", nargs="?", default="staging",
                       help="Environment to validate (staging/production)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    if not WEBSOCKETS_AVAILABLE:
        print("ERROR: websockets library not available")
        print("Install with: pip install websockets")
        sys.exit(2)
    
    try:
        validator = WebSocketDeploymentValidator(args.environment)
        success = asyncio.run(validator.run_validation())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Validation error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()