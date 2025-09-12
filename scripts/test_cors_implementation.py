#!/usr/bin/env python3
"""
Test script for verifying CORS implementation in Next.js API routes.

This script simulates CORS preflight requests and actual requests to verify
that the CORS implementation is working correctly across all frontend API routes.
"""

import asyncio
import aiohttp
import json
import sys
import time
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin
from shared.isolated_environment import IsolatedEnvironment


class CORSTestResult:
    def __init__(self, route: str, method: str, success: bool, details: str, response_headers: Dict[str, str] = None):
        self.route = route
        self.method = method
        self.success = success
        self.details = details
        self.response_headers = response_headers or {}


class CORSValidator:
    """Validates CORS implementation for Next.js API routes."""
    
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url
        self.test_origins = [
            "http://localhost:3000",
            "http://localhost:8000", 
            "https://app.staging.netrasystems.ai",
            "https://netra-frontend-701982941522.us-central1.run.app"
        ]
        self.routes = [
            "/api/health",
            "/api/config/public",
            "/api/threads",
            "/api/threads/test-thread-id"
        ]
        self.results: List[CORSTestResult] = []

    async def test_cors_preflight(self, session: aiohttp.ClientSession, route: str, origin: str) -> CORSTestResult:
        """Test CORS preflight (OPTIONS) request."""
        url = urljoin(self.base_url, route)
        headers = {
            'Origin': origin,
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Content-Type, Authorization'
        }
        
        try:
            async with session.options(url, headers=headers, timeout=aiohttp.ClientTimeout(total=5)) as response:
                response_headers = dict(response.headers)
                
                # Check required CORS headers
                required_headers = [
                    'Access-Control-Allow-Origin',
                    'Access-Control-Allow-Methods', 
                    'Access-Control-Allow-Headers',
                    'Access-Control-Allow-Credentials'
                ]
                
                missing_headers = [h for h in required_headers if h not in response_headers]
                
                if missing_headers:
                    return CORSTestResult(
                        route, "OPTIONS", False, 
                        f"Missing CORS headers: {missing_headers}", 
                        response_headers
                    )
                
                # Verify specific header values
                allow_origin = response_headers.get('Access-Control-Allow-Origin', '')
                allow_credentials = response_headers.get('Access-Control-Allow-Credentials', '').lower()
                
                if allow_origin != origin and allow_origin != '*':
                    return CORSTestResult(
                        route, "OPTIONS", False,
                        f"Invalid Allow-Origin: expected '{origin}' or '*', got '{allow_origin}'",
                        response_headers
                    )
                
                if allow_credentials != 'true':
                    return CORSTestResult(
                        route, "OPTIONS", False,
                        f"Invalid Allow-Credentials: expected 'true', got '{allow_credentials}'",
                        response_headers
                    )
                
                return CORSTestResult(
                    route, "OPTIONS", True,
                    f"CORS preflight successful (status: {response.status})",
                    response_headers
                )
                
        except asyncio.TimeoutError:
            return CORSTestResult(route, "OPTIONS", False, "Request timeout", {})
        except Exception as e:
            return CORSTestResult(route, "OPTIONS", False, f"Request failed: {str(e)}", {})

    async def test_cors_actual_request(self, session: aiohttp.ClientSession, route: str, origin: str) -> CORSTestResult:
        """Test actual request with CORS headers."""
        url = urljoin(self.base_url, route)
        headers = {'Origin': origin}
        
        try:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                response_headers = dict(response.headers)
                
                # Check if CORS headers are present in actual response
                allow_origin = response_headers.get('Access-Control-Allow-Origin', '')
                allow_credentials = response_headers.get('Access-Control-Allow-Credentials', '').lower()
                
                if not allow_origin:
                    return CORSTestResult(
                        route, "GET", False,
                        "Missing Access-Control-Allow-Origin header in actual response",
                        response_headers
                    )
                
                if allow_origin != origin and allow_origin != '*':
                    return CORSTestResult(
                        route, "GET", False,
                        f"Invalid Allow-Origin in actual response: expected '{origin}' or '*', got '{allow_origin}'",
                        response_headers
                    )
                
                return CORSTestResult(
                    route, "GET", True,
                    f"CORS actual request successful (status: {response.status})",
                    response_headers
                )
                
        except asyncio.TimeoutError:
            return CORSTestResult(route, "GET", False, "Request timeout", {})
        except Exception as e:
            return CORSTestResult(route, "GET", False, f"Request failed: {str(e)}", {})

    async def run_cors_tests(self) -> List[CORSTestResult]:
        """Run comprehensive CORS tests."""
        print(f"Testing CORS implementation at {self.base_url}")
        print(f"Testing {len(self.routes)} routes with {len(self.test_origins)} origins")
        print("=" * 60)
        
        connector = aiohttp.TCPConnector(limit=10)
        timeout = aiohttp.ClientTimeout(total=30)
        
        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            tasks = []
            
            # Test all combinations of routes and origins
            for route in self.routes:
                for origin in self.test_origins:
                    # Test preflight
                    tasks.append(self.test_cors_preflight(session, route, origin))
                    # Test actual request  
                    tasks.append(self.test_cors_actual_request(session, route, origin))
            
            # Execute all tests concurrently
            self.results = await asyncio.gather(*tasks, return_exceptions=False)
        
        return self.results

    def print_results(self):
        """Print detailed test results."""
        success_count = sum(1 for r in self.results if r.success)
        total_count = len(self.results)
        
        print(f"\nCORS Test Results: {success_count}/{total_count} passed")
        print("=" * 60)
        
        # Group results by route and method
        routes_tested = {}
        for result in self.results:
            key = f"{result.route} ({result.method})"
            if key not in routes_tested:
                routes_tested[key] = []
            routes_tested[key].append(result)
        
        for route_method, results in routes_tested.items():
            passed = sum(1 for r in results if r.success)
            total = len(results)
            status = " PASS:  PASS" if passed == total else " FAIL:  FAIL"
            print(f"{status} {route_method}: {passed}/{total}")
            
            # Show failures
            failures = [r for r in results if not r.success]
            for failure in failures:
                print(f"   FAIL:  {failure.details}")
        
        print("=" * 60)
        
        if success_count == total_count:
            print(" CELEBRATION:  All CORS tests passed! The implementation is working correctly.")
        else:
            print(" WARNING: [U+FE0F]  Some CORS tests failed. Check the implementation.")
            
    def export_results(self, filename: str = "cors_test_results.json"):
        """Export detailed results to JSON file."""
        export_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "base_url": self.base_url,
            "total_tests": len(self.results),
            "passed_tests": sum(1 for r in self.results if r.success),
            "routes_tested": self.routes,
            "origins_tested": self.test_origins,
            "results": [
                {
                    "route": r.route,
                    "method": r.method,
                    "success": r.success,
                    "details": r.details,
                    "response_headers": r.response_headers
                }
                for r in self.results
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"[U+1F4C4] Detailed results exported to {filename}")


async def main():
    """Main test execution."""
    base_url = "http://localhost:3000"
    
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    print("[U+1F9EA] CORS Implementation Validator")
    print(f"Target URL: {base_url}")
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    validator = CORSValidator(base_url)
    
    try:
        results = await validator.run_cors_tests()
        validator.print_results()
        validator.export_results()
        
        # Exit with appropriate code
        failed_count = sum(1 for r in results if not r.success)
        sys.exit(0 if failed_count == 0 else 1)
        
    except KeyboardInterrupt:
        print("\n[U+23F9][U+FE0F]  Test interrupted by user")
        sys.exit(130)
    except Exception as e:
        print(f"\n[U+1F4A5] Test execution failed: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    # Check if frontend server is likely running
    print("Note: Make sure your Next.js development server is running on the target URL")
    print("You can start it with: npm run dev (in the frontend directory)")
    print()
    
    asyncio.run(main())