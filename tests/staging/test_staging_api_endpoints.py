"""
Test 4: Staging Critical API Endpoints

CRITICAL: Test all critical API endpoints in staging environment.
This validates the core API functionality that drives platform value.

Business Value: Free/Early/Mid/Enterprise - Platform Core Functionality
Without working API endpoints, no platform features can function, blocking all user value.
"""

import pytest
import httpx
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from shared.isolated_environment import IsolatedEnvironment
from tests.staging.staging_config import StagingConfig

# Critical API Endpoints to Test
CRITICAL_ENDPOINTS = {
    "auth_service": [
        ("GET", "/health", "Health check endpoint"),
        ("POST", "/api/auth/simulate", "OAuth simulation for testing"), 
        ("POST", "/api/auth/refresh", "Token refresh endpoint"),
        ("POST", "/api/auth/logout", "User logout endpoint")
    ],
    "backend_service": [
        ("GET", "/health", "Health check endpoint"),
        ("GET", "/api/user/profile", "User profile endpoint"),
        ("POST", "/api/agents/execute", "Agent execution endpoint"),
        ("GET", "/api/agents/status", "Agent status endpoint"),
        ("POST", "/api/corpus/upload", "File upload endpoint"),
        ("GET", "/api/corpus/search", "Content search endpoint")
    ]
}

class StagingAPIEndpointsTestRunner:
    """Test runner for critical API endpoints in staging."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.environment = StagingConfig.get_environment()
        self.timeout = StagingConfig.TIMEOUTS["default"]
        self.access_token = None
        
    def get_base_headers(self) -> Dict[str, str]:
        """Get base headers for API requests."""
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Netra-Staging-API-Test/1.0"
        }
        
    def get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication."""
        headers = self.get_base_headers()
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
        
    async def get_test_token(self) -> Optional[str]:
        """Get test token for authenticated endpoints."""
        try:
            simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
            if not simulation_key:
                return None
                
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{StagingConfig.get_service_url('auth')}/api/auth/simulate",
                    headers=self.get_base_headers(),
                    json={
                        "simulation_key": simulation_key,
                        "user_id": "staging-api-test-user",
                        "email": "staging-api-test@netrasystems.ai"
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("access_token")
                    
        except Exception as e:
            print(f"Token generation failed: {e}")
            
        return None
        
    async def test_endpoint(self, service: str, method: str, endpoint: str, description: str, 
                          authenticated: bool = False, test_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Test a single API endpoint."""
        try:
            service_name = service.replace("_service", "")
            if service_name == "backend":
                service_name = "netra_backend"
            service_url = StagingConfig.get_service_url(service_name)
                
            full_url = f"{service_url}{endpoint}"
            headers = self.get_auth_headers() if authenticated else self.get_base_headers()
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                start_time = time.time()
                
                if method == "GET":
                    response = await client.get(full_url, headers=headers)
                elif method == "POST":
                    json_data = test_data or {}
                    response = await client.post(full_url, headers=headers, json=json_data)
                elif method == "PUT":
                    json_data = test_data or {}
                    response = await client.put(full_url, headers=headers, json=json_data)
                elif method == "DELETE":
                    response = await client.delete(full_url, headers=headers)
                else:
                    return {
                        "success": False,
                        "error": f"Unsupported method: {method}",
                        "endpoint": endpoint
                    }
                    
                response_time = time.time() - start_time
                
                # Determine success based on status code and endpoint type
                expected_success_codes = [200, 201, 202, 204]
                expected_auth_failure_codes = [401, 403]
                expected_not_found_codes = [404]
                
                # For some endpoints, certain "error" codes are actually expected
                if authenticated and not self.access_token and response.status_code in expected_auth_failure_codes:
                    success = True  # Expected auth failure
                    status_type = "expected_auth_failure"
                elif response.status_code in expected_success_codes:
                    success = True
                    status_type = "success"
                elif response.status_code in expected_not_found_codes and "profile" in endpoint:
                    success = True  # User profile might not exist yet
                    status_type = "expected_not_found"
                else:
                    success = response.status_code < 500  # Server errors are failures
                    status_type = "error" if response.status_code >= 500 else "client_error"
                    
                return {
                    "success": success,
                    "status_code": response.status_code,
                    "status_type": status_type,
                    "response_time": response_time,
                    "endpoint": endpoint,
                    "method": method,
                    "service": service,
                    "description": description,
                    "response_size": len(response.content) if response.content else 0,
                    "content_type": response.headers.get("content-type", ""),
                    "error": None if success else response.text[:500]  # Truncate error
                }
                
        except httpx.TimeoutException:
            return {
                "success": False,
                "status_code": 0,
                "status_type": "timeout",
                "response_time": self.timeout,
                "endpoint": endpoint,
                "method": method,
                "service": service,
                "description": description,
                "error": f"Request timed out after {self.timeout}s"
            }
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "status_type": "exception",
                "response_time": 0,
                "endpoint": endpoint,
                "method": method,
                "service": service,
                "description": description,
                "error": f"Request failed: {str(e)}"
            }
            
    async def test_auth_service_endpoints(self) -> Dict[str, Any]:
        """Test 4.1: Auth service critical endpoints."""
        print("4.1 Testing auth service endpoints...")
        
        results = {}
        endpoints = CRITICAL_ENDPOINTS["auth_service"]
        
        for method, endpoint, description in endpoints:
            print(f"     Testing {method} {endpoint}...")
            
            # Special handling for different endpoints
            test_data = None
            authenticated = False
            
            if endpoint == "/api/auth/simulate":
                simulation_key = self.env.get("E2E_OAUTH_SIMULATION_KEY")
                test_data = {
                    "simulation_key": simulation_key or "test-key",
                    "user_id": "staging-api-test-user",
                    "email": "staging-api-test@netrasystems.ai"
                }
            elif endpoint == "/api/auth/refresh":
                test_data = {"refresh_token": "dummy-refresh-token"}  # Will fail gracefully
            elif endpoint == "/api/auth/logout":
                authenticated = True
                
            result = await self.test_endpoint("auth_service", method, endpoint, description, 
                                           authenticated, test_data)
            results[endpoint.replace("/", "_").replace("-", "_")] = result
            
        return results
        
    async def test_backend_service_endpoints(self) -> Dict[str, Any]:
        """Test 4.2: Backend service critical endpoints."""
        print("4.2 Testing backend service endpoints...")
        
        results = {}
        endpoints = CRITICAL_ENDPOINTS["backend_service"]
        
        for method, endpoint, description in endpoints:
            print(f"     Testing {method} {endpoint}...")
            
            # Special handling for different endpoints
            test_data = None
            authenticated = True  # Most backend endpoints require auth
            
            if endpoint == "/health":
                authenticated = False
            elif endpoint == "/api/agents/execute":
                test_data = {
                    "query": "Test staging environment connectivity",
                    "agent_type": "supervisor",
                    "context": {"test_mode": True}
                }
            elif endpoint == "/api/corpus/upload":
                test_data = {
                    "content": "Test document content for staging",
                    "title": "Staging Test Document",
                    "type": "text"
                }
            elif endpoint == "/api/corpus/search":
                test_data = {
                    "query": "test",
                    "limit": 10
                }
                
            result = await self.test_endpoint("backend_service", method, endpoint, description,
                                           authenticated, test_data)
            results[endpoint.replace("/", "_").replace("-", "_")] = result
            
        return results
        
    async def test_cors_preflight_requests(self) -> Dict[str, Any]:
        """Test 4.3: CORS preflight requests for cross-origin access."""
        print("4.3 Testing CORS preflight requests...")
        
        results = {}
        
        # Test CORS preflight for both services
        services_to_test = ["auth", "backend"]
        
        for service in services_to_test:
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    # Send OPTIONS request (preflight)
                    response = await client.options(
                        f"{StagingConfig.get_service_url(service)}/api/test",
                        headers={
                            "Origin": StagingConfig.get_service_url("frontend"),
                            "Access-Control-Request-Method": "POST",
                            "Access-Control-Request-Headers": "Content-Type,Authorization"
                        }
                    )
                    
                    cors_headers = {
                        "access_control_allow_origin": response.headers.get("access-control-allow-origin"),
                        "access_control_allow_methods": response.headers.get("access-control-allow-methods"),
                        "access_control_allow_headers": response.headers.get("access-control-allow-headers"),
                        "access_control_allow_credentials": response.headers.get("access-control-allow-credentials")
                    }
                    
                    # CORS is working if we get 200/204 and proper headers
                    cors_working = (response.status_code in [200, 204] and
                                  cors_headers["access_control_allow_origin"] is not None)
                    
                    results[f"{service}_cors"] = {
                        "success": cors_working,
                        "status_code": response.status_code,
                        "cors_headers": cors_headers,
                        "service": service
                    }
                    
            except Exception as e:
                results[f"{service}_cors"] = {
                    "success": False,
                    "error": f"CORS test failed: {str(e)}",
                    "service": service
                }
                
        return results
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all API endpoint tests."""
        print(f"[U+1F50C] Running Critical API Endpoints Tests")
        print(f"Environment: {self.environment}")
        print(f"Auth URL: {StagingConfig.get_service_url('auth')}")
        print(f"Backend URL: {StagingConfig.get_service_url('netra_backend')}")
        print()
        
        # Get test token first
        print("[U+1F511] Getting test token...")
        self.access_token = await self.get_test_token()
        print(f"     Token obtained: {bool(self.access_token)}")
        print()
        
        results = {}
        
        # Test 4.1: Auth service endpoints
        auth_results = await self.test_auth_service_endpoints()
        results.update(auth_results)
        
        # Test 4.2: Backend service endpoints  
        backend_results = await self.test_backend_service_endpoints()
        results.update(backend_results)
        
        # Test 4.3: CORS preflight
        cors_results = await self.test_cors_preflight_requests()
        results.update(cors_results)
        
        # Calculate summary
        all_tests = {k: v for k, v in results.items() if isinstance(v, dict) and "success" in v}
        total_tests = len(all_tests)
        passed_tests = sum(1 for result in all_tests.values() if result["success"])
        
        # Identify critical failures (5xx errors)
        critical_failures = [
            result for result in all_tests.values() 
            if not result["success"] and result.get("status_code", 0) >= 500
        ]
        
        # Identify service availability issues
        health_check_failures = [
            result for result in all_tests.values()
            if "health" in result.get("endpoint", "") and not result["success"]
        ]
        
        results["summary"] = {
            "all_tests_passed": passed_tests == total_tests,
            "environment": self.environment,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "critical_failures": len(critical_failures),
            "health_check_failures": len(health_check_failures),
            "services_available": len(health_check_failures) == 0,
            "token_obtained": bool(self.access_token)
        }
        
        print()
        print(f" CHART:  Summary: {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed")
        print(f"[U+1F3E5] Health checks: {' PASS:  All services healthy' if results['summary']['services_available'] else ' FAIL:  Service issues detected'}")
        print(f" ALERT:  Critical failures: {results['summary']['critical_failures']}")
        
        if not results["summary"]["services_available"]:
            print(" ALERT:  CRITICAL: Service health check failures detected!")
            
        return results


@pytest.mark.asyncio
@pytest.mark.staging
async def test_staging_api_endpoints():
    """Main test entry point for critical API endpoints."""
    runner = StagingAPIEndpointsTestRunner()
    results = await runner.run_all_tests()
    
    # Assert critical conditions
    assert results["summary"]["services_available"], "Service health checks failed"
    assert results["summary"]["critical_failures"] == 0, f"Critical API failures: {results['summary']['critical_failures']}"
    assert results["summary"]["passed_tests"] >= results["summary"]["total_tests"] * 0.8, "Too many API endpoint failures"


if __name__ == "__main__":
    async def main():
        runner = StagingAPIEndpointsTestRunner()
        results = await runner.run_all_tests()
        
        if not results["summary"]["services_available"] or results["summary"]["critical_failures"] > 0:
            exit(1)
            
    asyncio.run(main())