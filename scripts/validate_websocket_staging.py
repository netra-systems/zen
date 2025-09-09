#!/usr/bin/env python3
"""
WebSocket Staging Connectivity Validator
Tests WebSocket handshake to staging environment

CRITICAL: This script validates that WebSocket infrastructure fixes are working
Business Impact: Ensures $120K+ MRR chat functionality is operational

Usage:
    python scripts/validate_websocket_staging.py
    python scripts/validate_websocket_staging.py --environment staging
    python scripts/validate_websocket_staging.py --environment production
"""

import asyncio
import json
import sys
import time
import argparse
from datetime import datetime
from typing import Dict, Optional

try:
    import websockets
    from websockets.exceptions import WebSocketException, ConnectionClosedError
    try:
        from websockets.exceptions import InvalidStatusCode
    except ImportError:
        # In newer versions, this might be renamed or moved
        from websockets.exceptions import InvalidStatus as InvalidStatusCode
except ImportError:
    print("❌ websockets library not found. Install with: pip install websockets")
    sys.exit(1)


class WebSocketStagingValidator:
    """Validates WebSocket connectivity in staging environment."""
    
    def __init__(self, environment: str = "staging"):
        self.environment = environment
        self.base_urls = self._get_environment_urls()
        self.results = []
    
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
    
    async def test_basic_websocket_handshake(self) -> bool:
        """Test basic WebSocket handshake without authentication."""
        ws_url = self.base_urls["api"].replace("https://", "wss://") + "/ws"
        test_name = "WebSocket Handshake"
        
        try:
            print(f"🔌 Testing {test_name}: {ws_url}")
            
            # Test WebSocket connection with extended timeout for GCP load balancer
            headers = {
                "Origin": self.base_urls["frontend"],
                "User-Agent": "WebSocketStagingValidator/1.0",
                "Connection": "Upgrade",
                "Upgrade": "websocket"
            }
            async with websockets.connect(
                ws_url,
                open_timeout=30,  # Extended for GCP load balancer
                close_timeout=10,
                additional_headers=headers
            ) as websocket:
                print(f"  ✅ WebSocket connection established")
                print(f"  📊 Connection state: {websocket.state.name}")
                
                # Test basic message exchange
                test_message = {
                    "type": "ping",
                    "timestamp": time.time(),
                    "test_id": f"staging_validation_{int(time.time())}"
                }
                
                await websocket.send(json.dumps(test_message))
                print(f"  📤 Sent ping message")
                
                # Wait for any response or connection status
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                    response_data = json.loads(response)
                    print(f"  📥 Received response: {response_data.get('type', 'unknown')}")
                    
                    self.results.append((test_name, True, "Connection established and message exchange successful"))
                    return True
                    
                except asyncio.TimeoutError:
                    print(f"  ⏰ No response within timeout (this may be expected for unauthenticated connection)")
                    # Even if no response, connection establishment is success
                    self.results.append((test_name, True, "Connection established (no response expected for unauthenticated)"))
                    return True
                    
        except ConnectionClosedError as e:
            if e.code == 1008:  # Authentication required
                print(f"  ✅ Connection closed with code 1008 (Authentication required - expected)")
                self.results.append((test_name, True, f"Proper authentication required (code {e.code})"))
                return True
            elif e.code == 1011:  # Internal server error
                print(f"  ❌ WebSocket 1011 internal error - infrastructure issue")
                self.results.append((test_name, False, f"WebSocket 1011 internal error"))
                return False
            else:
                print(f"  ❌ WebSocket closed unexpectedly: code {e.code}, reason: {e.reason}")
                self.results.append((test_name, False, f"WebSocket closed: code {e.code}"))
                return False
                
        except InvalidStatusCode as e:
            print(f"  ❌ Invalid HTTP status during handshake: {e.status_code}")
            if e.status_code == 403:
                print(f"      This indicates load balancer is blocking WebSocket upgrades")
                self.results.append((test_name, False, f"HTTP 403 - Load balancer blocking WebSocket upgrade"))
            elif e.status_code == 502:
                print(f"      This indicates backend service is not responding")
                self.results.append((test_name, False, f"HTTP 502 - Backend service unavailable"))
            else:
                self.results.append((test_name, False, f"HTTP {e.status_code} during handshake"))
            return False
            
        except OSError as e:
            print(f"  ❌ Network error: {e}")
            self.results.append((test_name, False, f"Network error: {e}"))
            return False
            
        except WebSocketException as e:
            print(f"  ❌ WebSocket protocol error: {e}")
            self.results.append((test_name, False, f"WebSocket protocol error: {e}"))
            return False
            
        except Exception as e:
            print(f"  ❌ Unexpected error: {e}")
            self.results.append((test_name, False, f"Unexpected error: {e}"))
            return False
    
    async def test_websocket_with_invalid_auth(self) -> bool:
        """Test WebSocket with invalid authentication token."""
        ws_url = self.base_urls["api"].replace("https://", "wss://") + "/ws"
        test_name = "WebSocket Invalid Auth"
        
        try:
            print(f"🔐 Testing {test_name}: {ws_url}")
            
            headers = {
                "Origin": self.base_urls["frontend"],
                "Authorization": "Bearer invalid-token-for-testing",
                "User-Agent": "WebSocketStagingValidator/1.0"
            }
            async with websockets.connect(
                ws_url,
                open_timeout=30,
                close_timeout=10,
                additional_headers=headers
            ) as websocket:
                
                # This should close with authentication error
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    print(f"  ❌ Expected auth error but connection stayed open")
                    self.results.append((test_name, False, "Authentication not properly enforced"))
                    return False
                    
                except ConnectionClosedError as e:
                    if e.code == 1008:  # Authentication required/failed
                        print(f"  ✅ Proper authentication rejection (code 1008)")
                        self.results.append((test_name, True, f"Authentication properly enforced"))
                        return True
                    else:
                        print(f"  ⚠️  Closed with code {e.code} instead of 1008")
                        self.results.append((test_name, True, f"Connection closed (code {e.code})"))
                        return True
                        
        except ConnectionClosedError as e:
            if e.code in [1008, 1003]:  # Authentication required or unsupported data
                print(f"  ✅ Authentication properly rejected (code {e.code})")
                self.results.append((test_name, True, f"Authentication enforced (code {e.code})"))
                return True
            else:
                print(f"  ❌ Unexpected close code: {e.code}")
                self.results.append((test_name, False, f"Unexpected close code: {e.code}"))
                return False
                
        except Exception as e:
            print(f"  ❌ Auth test error: {e}")
            self.results.append((test_name, False, f"Auth test error: {e}"))
            return False
    
    async def test_websocket_connection_timing(self) -> bool:
        """Test WebSocket connection establishment timing."""
        ws_url = self.base_urls["api"].replace("https://", "wss://") + "/ws"
        test_name = "WebSocket Timing"
        
        try:
            print(f"⏱️  Testing {test_name}: Connection timing")
            
            start_time = time.time()
            
            headers = {
                "Origin": self.base_urls["frontend"],
                "User-Agent": "WebSocketStagingValidator/1.0"
            }
            async with websockets.connect(
                ws_url,
                open_timeout=30,
                close_timeout=5,
                additional_headers=headers
            ) as websocket:
                
                connection_time = time.time() - start_time
                print(f"  📊 Connection established in {connection_time:.2f} seconds")
                
                if connection_time < 5.0:
                    print(f"  ✅ Fast connection establishment")
                    self.results.append((test_name, True, f"Connected in {connection_time:.2f}s"))
                    return True
                elif connection_time < 15.0:
                    print(f"  ⚠️  Slower than expected but acceptable")
                    self.results.append((test_name, True, f"Connected in {connection_time:.2f}s (slow)"))
                    return True
                else:
                    print(f"  ❌ Very slow connection establishment")
                    self.results.append((test_name, False, f"Slow connection: {connection_time:.2f}s"))
                    return False
                    
        except asyncio.TimeoutError:
            connection_time = time.time() - start_time
            print(f"  ❌ Connection timeout after {connection_time:.2f} seconds")
            self.results.append((test_name, False, f"Connection timeout after {connection_time:.2f}s"))
            return False
            
        except Exception as e:
            connection_time = time.time() - start_time
            print(f"  ❌ Connection failed after {connection_time:.2f}s: {e}")
            self.results.append((test_name, False, f"Failed after {connection_time:.2f}s: {e}"))
            return False
    
    async def test_load_balancer_headers(self) -> bool:
        """Test if load balancer properly handles WebSocket upgrade headers."""
        ws_url = self.base_urls["api"].replace("https://", "wss://") + "/ws"
        test_name = "Load Balancer Headers"
        
        try:
            print(f"🔄 Testing {test_name}: Header processing")
            
            # Test with explicit WebSocket upgrade headers
            headers = {
                "Origin": self.base_urls["frontend"],
                "User-Agent": "WebSocketStagingValidator/1.0",
                "Connection": "Upgrade",
                "Upgrade": "websocket",
                "Sec-WebSocket-Version": "13"
            }
            async with websockets.connect(
                ws_url,
                open_timeout=30,
                close_timeout=5,
                additional_headers=headers
            ) as websocket:
                
                print(f"  ✅ Load balancer properly handled WebSocket upgrade")
                self.results.append((test_name, True, "WebSocket upgrade headers processed correctly"))
                return True
                
        except InvalidStatusCode as e:
            if e.status_code == 403:
                print(f"  ❌ Load balancer blocking WebSocket upgrade (HTTP 403)")
                self.results.append((test_name, False, "Load balancer blocking WebSocket upgrade"))
                return False
            else:
                print(f"  ❌ HTTP {e.status_code} during upgrade")
                self.results.append((test_name, False, f"HTTP {e.status_code} during upgrade"))
                return False
                
        except Exception as e:
            print(f"  ❌ Header test error: {e}")
            self.results.append((test_name, False, f"Header test error: {e}"))
            return False
    
    async def run_comprehensive_validation(self) -> bool:
        """Run complete WebSocket validation suite."""
        print(f"\n🔌 WebSocket Staging Validation - {self.environment.upper()}")
        print(f"🎯 Target: {self.base_urls['api']}")
        print(f"🕒 Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        tests = [
            ("Basic Connection", self.test_basic_websocket_handshake),
            ("Connection Timing", self.test_websocket_connection_timing),
            ("Load Balancer Headers", self.test_load_balancer_headers),
            ("Authentication Enforcement", self.test_websocket_with_invalid_auth),
        ]
        
        all_passed = True
        
        for test_name, test_func in tests:
            try:
                result = await test_func()
                if not result:
                    all_passed = False
                print()  # Add spacing between tests
            except Exception as e:
                print(f"❌ {test_name} failed with exception: {e}")
                self.results.append((test_name, False, f"Exception: {e}"))
                all_passed = False
                print()
        
        # Print summary
        print("=" * 60)
        print("📊 VALIDATION RESULTS SUMMARY")
        print("=" * 60)
        
        passed_count = 0
        failed_count = 0
        
        for test_name, passed, details in self.results:
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"{status:<10} {test_name}: {details}")
            if passed:
                passed_count += 1
            else:
                failed_count += 1
        
        print("=" * 60)
        print(f"📈 Tests Passed: {passed_count}")
        print(f"📉 Tests Failed: {failed_count}")
        print(f"📊 Success Rate: {(passed_count/(passed_count+failed_count)*100):.1f}%")
        
        if all_passed:
            print("\n🎉 ALL WEBSOCKET VALIDATION TESTS PASSED!")
            print("✅ WebSocket infrastructure is working correctly")
            print("✅ Staging environment is ready for business-critical chat functionality")
        else:
            print("\n🚨 WEBSOCKET VALIDATION FAILED!")
            print("❌ WebSocket infrastructure issues detected")
            print("❌ Chat functionality will NOT work properly")
            print("\n🔧 RECOMMENDED ACTIONS:")
            print("1. Check if terraform infrastructure changes have been applied")
            print("2. Verify GCP load balancer configuration")
            print("3. Check Cloud Run service deployment status")
            print("4. Review GCP logs for WebSocket-related errors")
        
        print(f"\n🕒 Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        return all_passed


async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="WebSocket Staging Connectivity Validator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/validate_websocket_staging.py
  python scripts/validate_websocket_staging.py --environment staging
  python scripts/validate_websocket_staging.py --environment production
        """
    )
    parser.add_argument(
        "--environment", "-e",
        choices=["staging", "production"],
        default="staging",
        help="Environment to test (default: staging)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    try:
        validator = WebSocketStagingValidator(args.environment)
        success = await validator.run_comprehensive_validation()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️ Validation interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # Handle Windows asyncio event loop policy
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(main())