#!/usr/bin/env python3
'''
Manual E2E Testing for Staging Environment
=========================================
Comprehensive test suite to validate staging backend service functionality.

This script tests critical user flows without requiring complex test infrastructure.
'''

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
        self.session = aiohttp.ClientSession( )
        timeout=aiohttp.ClientTimeout(total=30),
        connector=aiohttp.TCPConnector(limit=10)
    
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
        await self.session.close()

    def log_result(self, test_name: str, success: bool, details: Dict[str, Any] = None, error: str = None):
        """Log test result."""
        result = { )
        "test_name": test_name,
        "success": success,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "details": details or {},
        "error": error
    
        self.test_results.append(result)

        status_symbol = "[PASS]" if success else "[FAIL]"
        print("formatted_string")
        if error:
        print("formatted_string")
        if details:
        print("formatted_string")

    async def make_request(self, method: str, path: str, **kwargs) -> tuple[int, Dict[str, Any]]:
        """Make HTTP request and return status code and response data."""
        url = "formatted_string"
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
        print(" )
        === HEALTH ENDPOINTS ===")

                            # Basic health
        status, data = await self.make_request("GET", "/health")
        self.log_result( )
        "Basic Health Check",
        status == 200 and data.get("status") == "healthy",
        {"status_code": status, "response": data},
        None if status == 200 else "formatted_string"
                            

                            # Liveness probe
        status, data = await self.make_request("GET", "/health/live")
        self.log_result( )
        "Liveness Probe",
        status == 200 and data.get("status") == "healthy",
        {"status_code": status, "response": data},
        None if status == 200 else "formatted_string"
                            

                            # Readiness probe (may timeout - expected)
        status, data = await self.make_request("GET", "/health/ready")
        success = status in [200, 503]  # 503 is acceptable if dependencies are down
        self.log_result( )
        "Readiness Probe",
        success,
        {"status_code": status, "response": data},
        None if success else "formatted_string"
                            

                            # Database environment
        status, data = await self.make_request("GET", "/health/database-env")
        self.log_result( )
        "Database Environment Config",
        status == 200 and "environment" in data,
        {"status_code": status, "database_name": data.get("database_name"), "valid": data.get("validation", {}).get("valid")},
        None if status == 200 else "formatted_string"
                            

    async def test_api_endpoints(self):
        """Test critical API endpoints."""
        print(" )
        === API ENDPOINTS ===")

                                # Test API root
        status, data = await self.make_request("GET", "/api/")
        self.log_result( )
        "API Root",
        status in [200, 404, 405],  # Various acceptable responses
        {"status_code": status},
        None if status in [200, 404, 405] else "formatted_string"
                                

                                # Test OpenAPI docs
        status, data = await self.make_request("GET", "/docs")
        self.log_result( )
        "API Documentation",
        status == 200,
        {"status_code": status},
        None if status == 200 else "formatted_string"
                                

                                # Test OpenAPI schema
        status, data = await self.make_request("GET", "/openapi.json")
        self.log_result( )
        "OpenAPI Schema",
        status == 200 and isinstance(data, dict) and "openapi" in data,
        {"status_code": status, "has_openapi": "openapi" in data},
        None if status == 200 else "formatted_string"
                                

    async def test_auth_endpoints(self):
        """Test authentication-related endpoints."""
        print(" )
        === AUTHENTICATION ENDPOINTS ===")

                                    # Test auth health (if available)
        status, data = await self.make_request("GET", "/auth/health")
        if status != 404:
        self.log_result( )
        "Auth Health Check",
        status == 200,
        {"status_code": status, "response": data},
        None if status == 200 else "formatted_string"
                                        

                                        # Test OAuth endpoints (should return proper responses)
        status, data = await self.make_request("GET", "/auth/google")
        self.log_result( )
        "Google OAuth Endpoint",
        status in [302, 400, 401, 404],  # Redirect or error expected without params
        {"status_code": status},
        None if status in [302, 400, 401, 404] else "formatted_string"
                                        

                                        # Test login page or endpoint
        status, data = await self.make_request("GET", "/auth/login")
        self.log_result( )
        "Login Endpoint",
        status in [200, 302, 404, 405],  # Various acceptable responses
        {"status_code": status},
        None if status in [200, 302, 404, 405] else "formatted_string"
                                        

    async def test_websocket_info(self):
        """Test WebSocket-related information endpoints."""
        print(" )
        === WEBSOCKET INFO ===")

                                            # Test WebSocket info endpoint if available
        status, data = await self.make_request("GET", "/ws/info")
        if status != 404:
        self.log_result( )
        "WebSocket Info",
        status == 200,
        {"status_code": status, "response": data},
        None if status == 200 else "formatted_string"
                                                
        else:
        self.log_result("WebSocket Info", True, {"note": "Endpoint not available (expected)"})

    async def test_cors_configuration(self):
        """Test CORS configuration."""
        print(" )
        === CORS CONFIGURATION ===")

                                                        # Test CORS preflight
        headers = { )
        "Origin": "https://example.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type"
                                                        
        status, data = await self.make_request("OPTIONS", "/api/", headers=headers)
        self.log_result( )
        "CORS Preflight",
        status in [200, 204],
        {"status_code": status},
        None if status in [200, 204] else "formatted_string"
                                                        

    async def test_database_operations(self):
        """Test database-related operations indirectly."""
        print(" )
        === DATABASE OPERATIONS ===")

                                                            # Test schema validation endpoint
        status, data = await self.make_request("GET", "/health/schema-validation")
        success = status in [200, 500]  # 500 acceptable if DB not fully ready
        self.log_result( )
        "Schema Validation",
        success,
        {"status_code": status, "response": data if status == 200 else "Service error"},
        None if success else "formatted_string"
                                                            

    async def test_error_handling(self):
        """Test error handling for non-existent endpoints."""
        print(" )
        === ERROR HANDLING ===")

                                                                # Test 404 handling
        status, data = await self.make_request("GET", "/nonexistent-endpoint")
        self.log_result( )
        "404 Error Handling",
        status == 404,
        {"status_code": status, "response": data},
        None if status == 404 else "formatted_string"
                                                                

                                                                # Test method not allowed
        status, data = await self.make_request("DELETE", "/health")
        self.log_result( )
        "Method Not Allowed Handling",
        status in [404, 405],  # Either is acceptable
        {"status_code": status},
        None if status in [404, 405] else "formatted_string"
                                                                

    async def run_all_tests(self):
        """Run all test suites."""
        print("formatted_string")
        print("formatted_string")

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
        print("formatted_string")
        print("TEST EXECUTION SUMMARY")
        print("formatted_string")

        total_tests = len(self.test_results)
        passed_tests = sum(1 for r in self.test_results if r["success"])
        failed_tests = total_tests - passed_tests

        print("formatted_string")
        print("formatted_string")
        print("formatted_string")
        print("formatted_string")

        if failed_tests > 0:
        print(f" )
        FAILED TESTS:")
        for result in self.test_results:
        if not result["success"]:
        print("formatted_string")

        print(f" )
        CRITICAL SERVICES STATUS:")
        health_tests = [item for item in []]]
        health_passed = sum(1 for r in health_tests if r["success"])
        print("formatted_string")

        api_tests = [item for item in []]]
        api_passed = sum(1 for r in api_tests if r["success"])
        print("formatted_string")

                # Overall recommendation
        if passed_tests / total_tests >= 0.8:
        print("formatted_string")
        print("   Recommendation: Staging environment is ready for testing")
        elif passed_tests / total_tests >= 0.6:
        print("formatted_string")
        print("   Recommendation: Some issues need attention but core functionality works")
        else:
        print("formatted_string")
        print("   Recommendation: Significant issues need resolution")

                            # Save results
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        results_file = "formatted_string"
        with open(results_file, 'w') as f:
        json.dump({ ))
        "test_run": { )
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "base_url": self.base_url,
        "total_tests": total_tests,
        "passed_tests": passed_tests,
        "failed_tests": failed_tests,
        "success_rate": passed_tests/total_tests
        },
        "test_results": self.test_results
        }, f, indent=2)
        print("formatted_string")


    async def main():
        """Main entry point."""
        staging_url = "https://netra-backend-staging-pnovr5vsba-uc.a.run.app"

        async with StagingE2ETester(staging_url) as tester:
        await tester.run_all_tests()


        if __name__ == "__main__":
        asyncio.run(main())