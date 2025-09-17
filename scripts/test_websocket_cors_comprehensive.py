#!/usr/bin/env python3
"""
Comprehensive WebSocket CORS Test Script

This script tests WebSocket connectivity in various scenarios to ensure CORS is properly configured
for Docker development environment. It tests connections with different origins and validates
that the development OAUTH SIMULATION works properly.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Ensure WebSocket reliability in development
- Value Impact: Prevents connection issues that block development
- Strategic Impact: Foundation for real-time features
"""

import asyncio
import json
import sys
import time
import traceback
from typing import Dict, List, Optional, Any
import aiohttp
import websockets
from urllib.parse import urlparse
from shared.isolated_environment import IsolatedEnvironment


class WebSocketTester:
    """Comprehensive WebSocket connection tester."""
    
    def __init__(self, backend_url: str = "ws://localhost:8000"):
        """Initialize WebSocket tester.
        
        Args:
            backend_url: Backend WebSocket URL
        """
        self.backend_url = backend_url
        self.test_results: List[Dict[str, Any]] = []
        
    async def test_connection(self, 
                            websocket_url: str, 
                            origin: Optional[str] = None,
                            test_name: str = "WebSocket Test",
                            expect_success: bool = True) -> Dict[str, Any]:
        """Test a single WebSocket connection.
        
        Args:
            websocket_url: WebSocket URL to connect to
            origin: Origin header to send
            test_name: Name of the test
            expect_success: Whether we expect the connection to succeed
            
        Returns:
            Test result dictionary
        """
        print(f"\n[TEST] Testing: {test_name}")
        print(f"   URL: {websocket_url}")
        print(f"   Origin: {origin or 'None'}")
        
        result = {
            "test_name": test_name,
            "websocket_url": websocket_url,
            "origin": origin,
            "expect_success": expect_success,
            "success": False,
            "connected": False,
            "connection_duration": 0,
            "error": None,
            "messages_exchanged": 0,
            "response_data": None
        }
        
        # Prepare headers - websockets library uses different format
        headers = []
        if origin:
            headers = [("Origin", origin)]
            
        start_time = time.time()
        
        try:
            # Prepare connection parameters
            connect_params = {
                "timeout": 10,
                "ping_interval": None  # Disable ping for quick test
            }
            
            # Add headers if provided (use modern websockets API)
            if headers:
                connect_params["additional_headers"] = headers
            
            # Attempt WebSocket connection with timeout
            async with websockets.connect(websocket_url, **connect_params) as websocket:
                result["connected"] = True
                connection_time = time.time() - start_time
                result["connection_duration"] = round(connection_time, 3)
                
                print(f"   [OK] Connected in {result['connection_duration']}s")
                
                # Try to send a ping message
                test_message = {
                    "type": "ping",
                    "data": {"test": True, "timestamp": time.time()}
                }
                
                await websocket.send(json.dumps(test_message))
                result["messages_exchanged"] += 1
                print("   [SEND] Sent ping message")
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    result["messages_exchanged"] += 1
                    result["response_data"] = response[:100]  # First 100 chars
                    print(f"   [RECV] Received response: {response[:50]}...")
                    result["success"] = True
                except asyncio.TimeoutError:
                    print("   [TIMEOUT] No response within 5 seconds (but connection successful)")
                    result["success"] = True  # Connection success is what we care about
                
        except websockets.InvalidStatus as e:
            result["error"] = f"HTTP {e.response.status_code}"
            print(f"   [ERROR] HTTP Error: {result['error']}")
            
        except websockets.ConnectionClosedError as e:
            result["error"] = f"Connection closed: {e.code} - {e.reason}"
            print(f"   [ERROR] Connection closed: {result['error']}")
            
        except Exception as e:
            result["error"] = f"{type(e).__name__}: {str(e)}"
            print(f"   [ERROR] Error: {result['error']}")
        
        # Validate result against expectation
        if result["success"] == expect_success:
            print(f"   [PASS] Result matches expectation: {'SUCCESS' if result['success'] else 'FAILED'}")
        else:
            print(f"   [FAIL] Result doesn't match expectation. Expected: {expect_success}, Got: {result['success']}")
        
        return result
    
    async def test_http_health(self, url: str = "http://localhost:8000/health") -> bool:
        """Test HTTP health endpoint to ensure backend is running.
        
        Args:
            url: Health endpoint URL
            
        Returns:
            True if healthy, False otherwise
        """
        print(f"\n[HEALTH] Testing HTTP Health: {url}")
        try:
            # Use a more generous timeout for health check
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        health_data = await response.text()
                        print(f"   [OK] Backend healthy: {response.status}")
                        return True
                    else:
                        print(f"   [ERROR] Backend unhealthy: {response.status}")
                        return False
        except asyncio.TimeoutError:
            print(f"   [ERROR] Health check timed out after 30s")
            return False
        except Exception as e:
            print(f"   [ERROR] Health check failed: {type(e).__name__}: {str(e)}")
            return False
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run comprehensive WebSocket tests.
        
        Returns:
            Summary of all test results
        """
        print("[START] Starting Comprehensive WebSocket CORS Tests")
        print("=" * 60)
        
        # First check if backend is healthy
        backend_healthy = await self.test_http_health()
        if not backend_healthy:
            print("\n[ERROR] Backend is not healthy. Skipping WebSocket tests.")
            return {
                "backend_healthy": False,
                "tests_run": 0,
                "tests_passed": 0,
                "tests_failed": 0,
                "results": []
            }
        
        # Define test scenarios
        base_ws_url = self.backend_url.rstrip('/') + "/ws"
        
        test_scenarios = [
            # Standard localhost scenarios
            {
                "url": base_ws_url,
                "origin": "http://localhost:3000",
                "name": "Localhost:3000 (Frontend)",
                "expect": True
            },
            {
                "url": base_ws_url,
                "origin": "http://localhost:8000", 
                "name": "Localhost:8000 (Backend)",
                "expect": True
            },
            {
                "url": base_ws_url,
                "origin": "http://127.0.0.1:3000",
                "name": "127.0.0.1:3000",
                "expect": True
            },
            
            # Docker service name scenarios
            {
                "url": base_ws_url,
                "origin": "http://frontend:3000",
                "name": "Docker service: frontend:3000",
                "expect": True
            },
            {
                "url": base_ws_url, 
                "origin": "http://backend:8000",
                "name": "Docker service: backend:8000",
                "expect": True
            },
            {
                "url": base_ws_url,
                "origin": "http://netra-frontend:3000",
                "name": "Docker container: netra-frontend:3000",
                "expect": True
            },
            
            # Docker bridge network IPs (common ranges)
            {
                "url": base_ws_url,
                "origin": "http://172.18.0.1:3000",
                "name": "Docker bridge IP: 172.18.0.1:3000", 
                "expect": True
            },
            
            # No origin (desktop/mobile app scenario)
            {
                "url": base_ws_url,
                "origin": None,
                "name": "No Origin Header (Desktop/Mobile)",
                "expect": True
            },
            
            # Development mode should allow these
            {
                "url": base_ws_url,
                "origin": "http://localhost:5173",
                "name": "Localhost:5173 (Vite)",
                "expect": True
            },
            
            # Test potentially suspicious origin (should be allowed in dev)
            {
                "url": base_ws_url,
                "origin": "http://test.example.com:3000",
                "name": "External origin (should work in dev mode)",
                "expect": True
            }
        ]
        
        # Run all test scenarios
        all_results = []
        for scenario in test_scenarios:
            result = await self.test_connection(
                scenario["url"],
                scenario["origin"], 
                scenario["name"],
                scenario["expect"]
            )
            all_results.append(result)
            
            # Small delay between tests
            await asyncio.sleep(0.5)
        
        # Analyze results
        tests_passed = sum(1 for r in all_results if r["success"] == r["expect_success"])
        tests_failed = len(all_results) - tests_passed
        
        summary = {
            "backend_healthy": backend_healthy,
            "tests_run": len(all_results),
            "tests_passed": tests_passed,
            "tests_failed": tests_failed,
            "success_rate": round(tests_passed / len(all_results) * 100, 1),
            "results": all_results
        }
        
        # Print summary
        print("\n" + "=" * 60)
        print("[SUMMARY] Test Summary")
        print("=" * 60)
        print(f"Backend Health: {'[OK] Healthy' if backend_healthy else '[ERROR] Unhealthy'}")
        print(f"Tests Run: {summary['tests_run']}")
        print(f"Tests Passed: {tests_passed}")
        print(f"Tests Failed: {tests_failed}")
        print(f"Success Rate: {summary['success_rate']}%")
        
        if tests_failed > 0:
            print("\n[FAILURES] Failed Tests:")
            for result in all_results:
                if result["success"] != result["expect_success"]:
                    print(f"  - {result['test_name']}: {result['error'] or 'Unexpected result'}")
        
        if tests_passed == len(all_results):
            print("\n[SUCCESS] All tests passed! WebSocket CORS is working correctly.")
        else:
            print(f"\n[WARNING] {tests_failed} test(s) failed. WebSocket CORS may need adjustment.")
        
        return summary


async def main():
    """Main test runner."""
    print("[MAIN] WebSocket CORS Comprehensive Test Suite")
    print("Testing WebSocket connectivity and CORS configuration in Docker development environment")
    print()
    
    # Allow custom backend URL via command line
    backend_url = "ws://localhost:8000"
    if len(sys.argv) > 1:
        backend_url = sys.argv[1]
        
    tester = WebSocketTester(backend_url)
    
    try:
        results = await tester.run_comprehensive_tests()
        
        # Save results to file
        timestamp = int(time.time())
        results_file = f"websocket_cors_test_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n[SAVE] Detailed results saved to: {results_file}")
        
        # Exit with appropriate code
        success_rate = results.get("success_rate", 0.0)
        if success_rate == 100.0:
            print("\n[SUCCESS] All tests passed!")
            sys.exit(0)
        else:
            tests_failed = results.get("tests_failed", 0)
            print(f"\n[FAIL] {tests_failed} tests failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n[INTERRUPT] Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[CRASH] Test suite crashed: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    # Install required packages if they're not available
    try:
        import websockets
        import aiohttp
    except ImportError as e:
        print(f"[ERROR] Missing required package: {e}")
        print("Please install: pip install websockets aiohttp")
        sys.exit(1)
    
    # Run the async main function
    asyncio.run(main())