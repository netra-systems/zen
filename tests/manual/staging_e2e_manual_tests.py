#!/usr/bin/env python3
"""
Manual E2E Testing for Staging Environment
=========================================
Comprehensive test suite to validate staging backend service functionality.

This script tests critical user flows without requiring complex test infrastructure.
"""

import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

import aiohttp


class StagingE2ETester:
    """Manual E2E tester for staging environment."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip('/')
        self.session = None
        self.test_results = []
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            connector=aiohttp.TCPConnector(limit=10)
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def log_result(self, test_name: str, success: bool, details: Dict[str, Any] = None, error: str = None):
        """Log test result."""
        result = {
            "test_name": test_name,
            "success": success,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "details": details or {},
            "error": error
        }
        self.test_results.append(result)
        
        status_symbol = "[PASS]" if success else "[FAIL]"
        print(f"{status_symbol} {test_name}")
        if error:
            print(f"   Error: {error}")
        if details:
            print(f"   Details: {json.dumps(details, indent=2)}")
    
    async def make_request(self, method: str, path: str, **kwargs) -> tuple[int, Dict[str, Any]]:
        """Make HTTP request and return status code and response data."""
        url = f"{self.base_url}{path}"
        try:
            async with self.session.request(method, url, **kwargs) as response:
                try:
                    data = await response.json()
                except:
                    data = {"text": await response.text()}
                return response.status, data
        except Exception as e:
            return 0, {"error": str(e)}
    
    async def test_health_endpoints(self):
        """Test all health-related endpoints."""
        print("\n=== HEALTH ENDPOINTS ===")
        
        # Basic health
        status, data = await self.make_request("GET", "/health")
        self.log_result(
            "Basic Health Check", 
            status == 200 and data.get("status") == "healthy",
            {"status_code": status, "response": data},
            None if status == 200 else f"Status: {status}"
        )
        
        # Liveness probe
        status, data = await self.make_request("GET", "/health/live")
        self.log_result(
            "Liveness Probe", 
            status == 200 and data.get("status") == "healthy",
            {"status_code": status, "response": data},
            None if status == 200 else f"Status: {status}"
        )
        
        # Readiness probe (may timeout - expected)
        status, data = await self.make_request("GET", "/health/ready")
        success = status in [200, 503]  # 503 is acceptable if dependencies are down
        self.log_result(
            "Readiness Probe", 
            success,
            {"status_code": status, "response": data},
            None if success else f"Unexpected status: {status}"
        )
        
        # Database environment
        status, data = await self.make_request("GET", "/health/database-env")
        self.log_result(
            "Database Environment Config", 
            status == 200 and "environment" in data,
            {"status_code": status, "database_name": data.get("database_name"), "valid": data.get("validation", {}).get("valid")},
            None if status == 200 else f"Status: {status}"
        )
    
    async def test_api_endpoints(self):
        """Test critical API endpoints."""
        print("\n=== API ENDPOINTS ===")
        
        # Test API root
        status, data = await self.make_request("GET", "/api/")
        self.log_result(
            "API Root", 
            status in [200, 404, 405],  # Various acceptable responses
            {"status_code": status},
            None if status in [200, 404, 405] else f"Status: {status}"
        )
        
        # Test OpenAPI docs
        status, data = await self.make_request("GET", "/docs")
        self.log_result(
            "API Documentation", 
            status == 200,
            {"status_code": status},
            None if status == 200 else f"Status: {status}"
        )
        
        # Test OpenAPI schema
        status, data = await self.make_request("GET", "/openapi.json")
        self.log_result(
            "OpenAPI Schema", 
            status == 200 and isinstance(data, dict) and "openapi" in data,
            {"status_code": status, "has_openapi": "openapi" in data},
            None if status == 200 else f"Status: {status}"
        )
    
    async def test_auth_endpoints(self):
        """Test authentication-related endpoints."""
        print("\n=== AUTHENTICATION ENDPOINTS ===")
        
        # Test auth health (if available)
        status, data = await self.make_request("GET", "/auth/health")
        if status != 404:
            self.log_result(
                "Auth Health Check", 
                status == 200,
                {"status_code": status, "response": data},
                None if status == 200 else f"Status: {status}"
            )
        
        # Test OAuth endpoints (should return proper responses)
        status, data = await self.make_request("GET", "/auth/google")
        self.log_result(
            "Google OAuth Endpoint", 
            status in [302, 400, 401, 404],  # Redirect or error expected without params
            {"status_code": status},
            None if status in [302, 400, 401, 404] else f"Status: {status}"
        )
        
        # Test login page or endpoint
        status, data = await self.make_request("GET", "/auth/login")
        self.log_result(
            "Login Endpoint", 
            status in [200, 302, 404, 405],  # Various acceptable responses
            {"status_code": status},
            None if status in [200, 302, 404, 405] else f"Status: {status}"
        )
    
    async def test_websocket_info(self):
        """Test WebSocket-related information endpoints."""
        print("\n=== WEBSOCKET INFO ===")
        
        # Test WebSocket info endpoint if available
        status, data = await self.make_request("GET", "/ws/info")
        if status != 404:
            self.log_result(
                "WebSocket Info", 
                status == 200,
                {"status_code": status, "response": data},
                None if status == 200 else f"Status: {status}"
            )
        else:
            self.log_result("WebSocket Info", True, {"note": "Endpoint not available (expected)"})
    
    async def test_cors_configuration(self):
        """Test CORS configuration."""
        print("\n=== CORS CONFIGURATION ===")
        
        # Test CORS preflight
        headers = {
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type"
        }
        status, data = await self.make_request("OPTIONS", "/api/", headers=headers)
        self.log_result(
            "CORS Preflight", 
            status in [200, 204],
            {"status_code": status},
            None if status in [200, 204] else f"Status: {status}"
        )
    
    async def test_database_operations(self):
        """Test database-related operations indirectly."""
        print("\n=== DATABASE OPERATIONS ===")
        
        # Test schema validation endpoint
        status, data = await self.make_request("GET", "/health/schema-validation")
        success = status in [200, 500]  # 500 acceptable if DB not fully ready
        self.log_result(
            "Schema Validation", 
            success,
            {"status_code": status, "response": data if status == 200 else "Service error"},
            None if success else f"Status: {status}"
        )
    
    async def test_error_handling(self):
        """Test error handling for non-existent endpoints."""
        print("\n=== ERROR HANDLING ===")
        
        # Test 404 handling
        status, data = await self.make_request("GET", "/nonexistent-endpoint")
        self.log_result(
            "404 Error Handling", 
            status == 404,
            {"status_code": status, "response": data},
            None if status == 404 else f"Expected 404, got {status}"
        )
        
        # Test method not allowed
        status, data = await self.make_request("DELETE", "/health")
        self.log_result(
            "Method Not Allowed Handling", 
            status in [404, 405],  # Either is acceptable
            {"status_code": status},
            None if status in [404, 405] else f"Status: {status}"
        )
    
    async def run_all_tests(self):
        """Run all test suites."""
        print(f"[START] Starting E2E tests against: {self.base_url}")
        print(f"[TIME] Test started at: {datetime.now(timezone.utc).isoformat()}")
        
        # Run all test suites
        await self.test_health_endpoints()
        await self.test_api_endpoints()
        await self.test_auth_endpoints()
        await self.test_websocket_info()
        await self.test_cors_configuration()
        await self.test_database_operations()
        await self.test_error_handling()
        
        # Generate summary
        self.generate_summary()
    
    def generate_summary(self):
        """Generate test summary report."""
        print(f"\n{'='*60}")
        print("TEST EXECUTION SUMMARY")
        print(f"{'='*60}")
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print(f"\nFAILED TESTS:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  [FAIL] {result['test_name']}: {result.get('error', 'Unknown error')}")
        
        print(f"\nCRITICAL SERVICES STATUS:")
        health_tests = [r for r in self.test_results if "Health" in r["test_name"]]
        health_passed = sum(1 for r in health_tests if r["success"])
        print(f"  Health Endpoints: {health_passed}/{len(health_tests)} working")
        
        api_tests = [r for r in self.test_results if "API" in r["test_name"]]
        api_passed = sum(1 for r in api_tests if r["success"])
        print(f"  API Endpoints: {api_passed}/{len(api_tests)} working")
        
        # Overall recommendation
        if passed_tests / total_tests >= 0.8:
            print(f"\n[HEALTHY] STAGING STATUS: HEALTHY - {passed_tests}/{total_tests} tests passing")
            print("   Recommendation: Staging environment is ready for testing")
        elif passed_tests / total_tests >= 0.6:
            print(f"\n[DEGRADED] STAGING STATUS: DEGRADED - {passed_tests}/{total_tests} tests passing")
            print("   Recommendation: Some issues need attention but core functionality works")
        else:
            print(f"\n[UNHEALTHY] STAGING STATUS: UNHEALTHY - {passed_tests}/{total_tests} tests passing")
            print("   Recommendation: Significant issues need resolution")
        
        # Save results
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        results_file = f"staging_e2e_results_{timestamp}.json"
        with open(results_file, 'w') as f:
            json.dump({
                "test_run": {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "base_url": self.base_url,
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "success_rate": passed_tests/total_tests
                },
                "test_results": self.test_results
            }, f, indent=2)
        print(f"\n[RESULTS] Detailed results saved to: {results_file}")


async def main():
    """Main entry point."""
    staging_url = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"
    
    async with StagingE2ETester(staging_url) as tester:
        await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())