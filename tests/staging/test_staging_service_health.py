"""
Test 5: Staging Service Health

CRITICAL: Verify all services are healthy and responding in staging environment.
This is the foundation test - if services aren't healthy, nothing else works.

Business Value: Platform/Internal - System Stability & Uptime
Unhealthy services block all user interactions, causing immediate revenue loss.
"""

import pytest
import httpx
import asyncio
import time
from typing import Dict, Any, List, Optional
from shared.isolated_environment import IsolatedEnvironment
from tests.staging.staging_config import StagingConfig

# Critical Services Configuration
CRITICAL_SERVICES = {
    "backend": {
        "name": "Backend Service",
        "health_endpoint": "/health",
        "required": True,
        "timeout": 15.0
    },
    "auth": {
        "name": "Auth Service", 
        "health_endpoint": "/health",
        "required": True,
        "timeout": 10.0
    },
    "frontend": {
        "name": "Frontend Service",
        "health_endpoint": "/",  # Frontend uses root for health
        "required": True,
        "timeout": 10.0
    }
}

class StagingServiceHealthTestRunner:
    """Test runner for service health validation in staging."""
    
    def __init__(self):
        self.env = IsolatedEnvironment()
        self.environment = StagingConfig.get_environment()  # Now defaults to 'staging'
        self.urls = {
            "backend": StagingConfig.get_service_url("NETRA_BACKEND"),
            "auth": StagingConfig.get_service_url("AUTH_SERVICE"),
            "frontend": StagingConfig.get_service_url("FRONTEND")
        }
        self.timeout = StagingConfig.TIMEOUTS["default"]
        
    def get_base_headers(self) -> Dict[str, str]:
        """Get base headers for health check requests."""
        return {
            "Accept": "application/json",
            "User-Agent": "Netra-Staging-Health-Check/1.0",
            "Cache-Control": "no-cache"
        }
        
    async def test_service_health(self, service_key: str) -> Dict[str, Any]:
        """Test health of a single service."""
        service_config = CRITICAL_SERVICES[service_key]
        service_url = self.urls[service_key]
        health_endpoint = service_config["health_endpoint"]
        service_timeout = service_config["timeout"]
        
        try:
            full_url = f"{service_url}{health_endpoint}"
            
            async with httpx.AsyncClient(timeout=service_timeout) as client:
                start_time = time.time()
                
                # Make health check request
                response = await client.get(
                    full_url,
                    headers=self.get_base_headers(),
                    follow_redirects=True  # Important for frontend
                )
                
                response_time = time.time() - start_time
                
                # Parse response data if available
                response_data = {}
                try:
                    if response.headers.get("content-type", "").startswith("application/json"):
                        response_data = response.json()
                except:
                    pass  # Not JSON response, that's ok for some services
                    
                # Determine health status
                is_healthy = response.status_code == 200
                
                # Additional checks for backend/auth services
                if service_key in ["backend", "auth"] and is_healthy:
                    # Check for expected health response structure
                    if isinstance(response_data, dict):
                        service_status = response_data.get("status", "unknown")
                        is_healthy = service_status in ["healthy", "ok", "running"]
                        
                return {
                    "success": is_healthy,
                    "service_name": service_config["name"],
                    "service_key": service_key,
                    "url": full_url,
                    "status_code": response.status_code,
                    "response_time": response_time,
                    "health_data": response_data,
                    "service_status": response_data.get("status") if isinstance(response_data, dict) else None,
                    "version": response_data.get("version") if isinstance(response_data, dict) else None,
                    "uptime": response_data.get("uptime") if isinstance(response_data, dict) else None,
                    "content_length": len(response.content) if response.content else 0,
                    "headers": dict(response.headers)
                }
                
        except httpx.TimeoutException:
            return {
                "success": False,
                "service_name": service_config["name"],
                "service_key": service_key,
                "url": f"{service_url}{health_endpoint}",
                "status_code": 0,
                "response_time": service_timeout,
                "error": f"Health check timed out after {service_timeout}s",
                "error_type": "timeout"
            }
        except httpx.ConnectError as e:
            return {
                "success": False,
                "service_name": service_config["name"],
                "service_key": service_key,
                "url": f"{service_url}{health_endpoint}",
                "status_code": 0,
                "response_time": 0,
                "error": f"Connection failed: {str(e)}",
                "error_type": "connection_error"
            }
        except Exception as e:
            return {
                "success": False,
                "service_name": service_config["name"],
                "service_key": service_key,
                "url": f"{service_url}{health_endpoint}",
                "status_code": 0,
                "response_time": 0,
                "error": f"Health check failed: {str(e)}",
                "error_type": "unknown_error"
            }
            
    async def test_service_dependencies(self) -> Dict[str, Any]:
        """Test 5.1: Check if services can reach their dependencies."""
        print("5.1 Testing service dependencies...")
        
        # For staging, we'll test some basic dependency connectivity
        results = {}
        
        # Test if backend can reach external dependencies (simulated)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Test external connectivity from staging environment
                external_test_url = "https://httpbin.org/status/200"
                response = await client.get(external_test_url)
                
                results["external_connectivity"] = {
                    "success": response.status_code == 200,
                    "description": "External network connectivity test",
                    "status_code": response.status_code,
                    "response_time": response.elapsed.total_seconds() if response.elapsed else 0
                }
        except Exception as e:
            results["external_connectivity"] = {
                "success": False,
                "description": "External network connectivity test",
                "error": f"External connectivity test failed: {str(e)}"
            }
            
        # Test DNS resolution
        try:
            import socket
            socket.gethostbyname("google.com")
            results["dns_resolution"] = {
                "success": True,
                "description": "DNS resolution test"
            }
        except Exception as e:
            results["dns_resolution"] = {
                "success": False,
                "description": "DNS resolution test",
                "error": f"DNS resolution failed: {str(e)}"
            }
            
        return results
        
    async def test_service_performance(self) -> Dict[str, Any]:
        """Test 5.2: Check service performance metrics."""
        print("5.2 Testing service performance...")
        
        results = {}
        
        # Test response times for all services
        for service_key in CRITICAL_SERVICES.keys():
            service_url = self.urls[service_key]
            
            try:
                # Multiple requests to get average response time
                response_times = []
                
                for i in range(3):  # 3 requests for average
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        start_time = time.time()
                        response = await client.get(
                            f"{service_url}{CRITICAL_SERVICES[service_key]['health_endpoint']}",
                            headers=self.get_base_headers()
                        )
                        response_time = time.time() - start_time
                        
                        if response.status_code == 200:
                            response_times.append(response_time)
                            
                if response_times:
                    avg_response_time = sum(response_times) / len(response_times)
                    max_response_time = max(response_times)
                    min_response_time = min(response_times)
                    
                    # Performance thresholds
                    performance_good = avg_response_time < 2.0  # 2 seconds
                    performance_acceptable = avg_response_time < 5.0  # 5 seconds
                    
                    results[f"{service_key}_performance"] = {
                        "success": performance_acceptable,
                        "service": service_key,
                        "avg_response_time": avg_response_time,
                        "max_response_time": max_response_time,
                        "min_response_time": min_response_time,
                        "performance_rating": "good" if performance_good else "acceptable" if performance_acceptable else "poor",
                        "requests_completed": len(response_times)
                    }
                else:
                    results[f"{service_key}_performance"] = {
                        "success": False,
                        "service": service_key,
                        "error": "No successful requests completed"
                    }
                    
            except Exception as e:
                results[f"{service_key}_performance"] = {
                    "success": False,
                    "service": service_key,
                    "error": f"Performance test failed: {str(e)}"
                }
                
        return results
        
    async def test_service_load_capacity(self) -> Dict[str, Any]:
        """Test 5.3: Basic load capacity test for services."""
        print("5.3 Testing service load capacity...")
        
        results = {}
        
        # Light load test - 10 concurrent requests to each service
        concurrent_requests = 10
        
        for service_key in ["backend", "auth"]:  # Skip frontend for load test
            service_url = self.urls[service_key]
            health_endpoint = CRITICAL_SERVICES[service_key]["health_endpoint"]
            
            try:
                async def make_request(client):
                    response = await client.get(
                        f"{service_url}{health_endpoint}",
                        headers=self.get_base_headers()
                    )
                    return response.status_code == 200, response.elapsed.total_seconds() if response.elapsed else 0
                    
                async with httpx.AsyncClient(timeout=15.0) as client:
                    # Execute concurrent requests
                    tasks = [make_request(client) for _ in range(concurrent_requests)]
                    start_time = time.time()
                    request_results = await asyncio.gather(*tasks, return_exceptions=True)
                    total_time = time.time() - start_time
                    
                    # Analyze results
                    successful_requests = 0
                    response_times = []
                    
                    for result in request_results:
                        if isinstance(result, tuple) and result[0]:
                            successful_requests += 1
                            response_times.append(result[1])
                            
                    success_rate = successful_requests / concurrent_requests
                    avg_response_time = sum(response_times) / len(response_times) if response_times else 0
                    
                    results[f"{service_key}_load_test"] = {
                        "success": success_rate >= 0.8,  # 80% success rate required
                        "service": service_key,
                        "concurrent_requests": concurrent_requests,
                        "successful_requests": successful_requests,
                        "success_rate": success_rate,
                        "total_time": total_time,
                        "avg_response_time": avg_response_time,
                        "requests_per_second": concurrent_requests / total_time if total_time > 0 else 0
                    }
                    
            except Exception as e:
                results[f"{service_key}_load_test"] = {
                    "success": False,
                    "service": service_key,
                    "error": f"Load test failed: {str(e)}"
                }
                
        return results
        
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all service health tests."""
        print(f"[U+1F3E5] Running Service Health Tests")
        print(f"Environment: {self.environment}")
        print()
        
        for service_key, config in CRITICAL_SERVICES.items():
            print(f"[U+1F517] {config['name']}: {self.urls[service_key]}")
        print()
        
        results = {}
        
        # Core health tests for each service
        print("Testing individual service health...")
        service_health_results = {}
        
        for service_key in CRITICAL_SERVICES.keys():
            print(f"     Testing {CRITICAL_SERVICES[service_key]['name']}...")
            health_result = await self.test_service_health(service_key)
            service_health_results[service_key] = health_result
            print(f"      PASS:  {CRITICAL_SERVICES[service_key]['name']}: {health_result['success']} ({health_result.get('response_time', 0):.2f}s)")
            
        results.update(service_health_results)
        
        # Dependency tests
        dependency_results = await self.test_service_dependencies()
        results.update(dependency_results)
        print(f"      PASS:  External connectivity: {dependency_results.get('external_connectivity', {}).get('success', False)}")
        print(f"      PASS:  DNS resolution: {dependency_results.get('dns_resolution', {}).get('success', False)}")
        
        # Performance tests
        performance_results = await self.test_service_performance()
        results.update(performance_results)
        
        # Load capacity tests
        load_results = await self.test_service_load_capacity()
        results.update(load_results)
        
        # Calculate summary
        service_tests = {k: v for k, v in results.items() if k in CRITICAL_SERVICES.keys()}
        all_services_healthy = all(result["success"] for result in service_tests.values())
        
        total_tests = len(results)
        passed_tests = sum(1 for result in results.values() if isinstance(result, dict) and result.get("success", False))
        
        critical_services_down = [
            service for service, result in service_tests.items() 
            if not result["success"] and CRITICAL_SERVICES[service]["required"]
        ]
        
        results["summary"] = {
            "all_services_healthy": all_services_healthy,
            "environment": self.environment,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "critical_services_down": critical_services_down,
            "system_operational": len(critical_services_down) == 0
        }
        
        print()
        print(f" CHART:  Summary: {results['summary']['passed_tests']}/{results['summary']['total_tests']} tests passed")
        print(f"[U+1F3E5] System status: {' PASS:  Operational' if results['summary']['system_operational'] else ' FAIL:  Critical services down'}")
        
        if critical_services_down:
            print(f" ALERT:  CRITICAL: Services down: {', '.join(critical_services_down)}")
            
        return results


@pytest.mark.asyncio
@pytest.mark.staging
async def test_staging_service_health():
    """Main test entry point for service health validation."""
    runner = StagingServiceHealthTestRunner()
    results = await runner.run_all_tests()
    
    # Assert critical conditions
    assert results["summary"]["system_operational"], f"Critical services down: {results['summary']['critical_services_down']}"
    assert results["summary"]["all_services_healthy"], "Not all services are healthy"
    assert len(results["summary"]["critical_services_down"]) == 0, "Critical services are not responding"


if __name__ == "__main__":
    async def main():
        runner = StagingServiceHealthTestRunner()
        results = await runner.run_all_tests()
        
        if not results["summary"]["system_operational"]:
            exit(1)
            
    asyncio.run(main())