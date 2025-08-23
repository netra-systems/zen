"""CORS Auth Service L4 Integration Test

Business Value Justification (BVJ):
- Segment: Free, Early, Mid, Enterprise
- Business Goal: Conversion (Users cannot even start trial without auth working)
- Value Impact: Enables authentication flow for 100% of users
- Revenue Impact: $50K MRR at risk if users cannot authenticate

Critical Path: Frontend CORS -> Auth Service -> Authentication Flow
Coverage: Real Docker containers, actual HTTP headers, browser-like requests
"""

import sys
from pathlib import Path

# Test framework import - using pytest fixtures instead

import asyncio
import json
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
import pytest
from testcontainers.compose import DockerCompose

from netra_backend.tests.integration.critical_paths.l4_staging_critical_base import (
    CriticalPathMetrics,
    L4StagingCriticalPathTestBase,
)

@dataclass
class CorsTestResult:
    """CORS test result container."""
    endpoint: str
    origin: str
    method: str
    preflight_success: bool
    actual_success: bool
    headers: Dict[str, str]
    response_time: float
    status_code: int

class CorsAuthServiceL4Test(L4StagingCriticalPathTestBase):
    """L4 CORS authentication service test with real containers."""
    
    def __init__(self):
        """Initialize CORS auth service L4 test."""
        super().__init__("cors_auth_service_l4")
        self.docker_compose: Optional[DockerCompose] = None
        self.auth_service_url: str = ""
        self.frontend_url: str = ""
        self.backend_url: str = ""
        self.test_origins = [
            "http://localhost:3001",  # Frontend dev
            "http://127.0.0.1:3001",  # Frontend alt
            "https://app.netrasystems.ai",   # Production frontend
            "https://staging.netrasystems.ai" # Staging frontend
        ]
        self.cors_results: List[CorsTestResult] = []
    
    async def setup_test_specific_environment(self) -> None:
        """Setup Docker containers for L4 CORS testing."""
        
        if not compose_file.exists():
            await self._create_staging_compose_file(compose_file)
        
        self.docker_compose = DockerCompose(
            str(compose_file.parent),
            compose_file_name="docker-compose.staging.yml"
        )
        
        # Start services with health checks
        self.docker_compose.start()
        
        # Wait for services to be ready
        await self._wait_for_services_ready()
        
        # Get service URLs from containers
        await self._discover_service_endpoints()
    
    async def _create_staging_compose_file(self, compose_file: Path) -> None:
        """Create staging Docker Compose configuration."""
        compose_content = {
            "version": "3.8",
            "services": {
                "auth-service": {
                    "build": {
                        "context": "../auth_service",
                        "dockerfile": "Dockerfile"
                    },
                    "ports": ["8081:8080"],
                    "environment": {
                        "ENVIRONMENT": "staging",
                        "DATABASE_URL": "postgresql://test:test@postgres:5432/netra_test",
                        "JWT_SECRET_KEY": "test-jwt-secret-key-32-characters-minimum",
                        "CORS_ORIGINS": "http://localhost:3001,http://127.0.0.1:3001,https://app.netrasystems.ai"
                    },
                    "depends_on": ["postgres"],
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:8080/health"],
                        "interval": "10s",
                        "timeout": "5s",
                        "retries": 5
                    }
                },
                "backend": {
                    "build": {
                        "context": "../app",
                        "dockerfile": "Dockerfile"
                    },
                    "ports": ["8000:8000"],
                    "environment": {
                        "ENVIRONMENT": "staging",
                        "DATABASE_URL": "postgresql://test:test@postgres:5432/netra_test",
                        "AUTH_SERVICE_URL": "http://auth-service:8080",
                        "CORS_ORIGINS": "http://localhost:3001,http://127.0.0.1:3001"
                    },
                    "depends_on": ["postgres", "auth-service"]
                },
                "frontend": {
                    "build": {
                        "context": "../frontend",
                        "dockerfile": "Dockerfile"
                    },
                    "ports": ["3001:3000"],
                    "environment": {
                        "NEXT_PUBLIC_API_BASE_URL": "http://localhost:8000",
                        "NEXT_PUBLIC_AUTH_SERVICE_URL": "http://localhost:8081"
                    }
                },
                "postgres": {
                    "image": "postgres:15",
                    "environment": {
                        "POSTGRES_DB": "netra_test",
                        "POSTGRES_USER": "test",
                        "POSTGRES_PASSWORD": "test"
                    },
                    "ports": ["5432:5432"]
                }
            }
        }
        
        compose_file.parent.mkdir(parents=True, exist_ok=True)
        with open(compose_file, 'w') as f:
            import yaml
            yaml.dump(compose_content, f)
    
    async def _wait_for_services_ready(self) -> None:
        """Wait for all services to be ready."""
        max_wait = 60  # 60 seconds maximum wait
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            try:
                # Check auth service health
                auth_ready = await self._check_service_health("auth-service", 8081)
                backend_ready = await self._check_service_health("backend", 8000)
                
                if auth_ready and backend_ready:
                    return
                    
            except Exception:
                pass
            
            await asyncio.sleep(2)
        
        raise RuntimeError("Services failed to become ready within timeout")
    
    async def _check_service_health(self, service_name: str, port: int) -> bool:
        """Check if service is healthy."""
        try:
            health_url = f"http://localhost:{port}/health"
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(health_url)
                return response.status_code == 200
        except Exception:
            return False
    
    async def _discover_service_endpoints(self) -> None:
        """Discover service endpoints from containers."""
        self.auth_service_url = "http://localhost:8081"
        self.frontend_url = "http://localhost:3001"
        self.backend_url = "http://localhost:8000"
    
    async def execute_critical_path_test(self) -> Dict[str, Any]:
        """Execute CORS auth service critical path test."""
        test_results = {
            "preflight_tests": [],
            "auth_config_tests": [],
            "websocket_tests": [],
            "multiple_origin_tests": [],
            "service_calls": 0
        }
        
        # Test 1: Preflight OPTIONS requests
        preflight_results = await self._test_preflight_requests()
        test_results["preflight_tests"] = preflight_results
        test_results["service_calls"] += len(preflight_results)
        
        # Test 2: Auth config endpoint with credentials
        auth_config_results = await self._test_auth_config_endpoint()
        test_results["auth_config_tests"] = auth_config_results
        test_results["service_calls"] += len(auth_config_results)
        
        # Test 3: WebSocket upgrade requests
        websocket_results = await self._test_websocket_cors()
        test_results["websocket_tests"] = websocket_results
        test_results["service_calls"] += len(websocket_results)
        
        # Test 4: Multiple origin validation
        multi_origin_results = await self._test_multiple_origins()
        test_results["multiple_origin_tests"] = multi_origin_results
        test_results["service_calls"] += len(multi_origin_results)
        
        return test_results
    
    async def _test_preflight_requests(self) -> List[Dict[str, Any]]:
        """Test CORS preflight OPTIONS requests."""
        preflight_results = []
        
        for origin in self.test_origins:
            result = await self._make_cors_request(
                f"{self.auth_service_url}/auth/config",
                method="OPTIONS",
                origin=origin,
                headers={
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "Authorization,Content-Type"
                }
            )
            
            preflight_results.append({
                "origin": origin,
                "success": result.status_code == 200,
                "has_cors_headers": self._has_required_cors_headers(result.headers),
                "response_time": result.response_time,
                "headers": dict(result.headers)
            })
        
        return preflight_results
    
    async def _test_auth_config_endpoint(self) -> List[Dict[str, Any]]:
        """Test auth config endpoint with CORS."""
        config_results = []
        
        for origin in self.test_origins:
            result = await self._make_cors_request(
                f"{self.auth_service_url}/auth/config",
                method="GET",
                origin=origin,
                headers={"Authorization": "Bearer test-token"}
            )
            
            config_results.append({
                "origin": origin,
                "success": result.status_code in [200, 401],  # 401 is ok (invalid token)
                "has_cors_headers": "Access-Control-Allow-Origin" in result.headers,
                "allows_credentials": result.headers.get("Access-Control-Allow-Credentials") == "true",
                "response_time": result.response_time
            })
        
        return config_results
    
    async def _test_websocket_cors(self) -> List[Dict[str, Any]]:
        """Test WebSocket upgrade with CORS headers."""
        websocket_results = []
        
        for origin in self.test_origins:
            result = await self._make_cors_request(
                f"{self.auth_service_url}/ws",
                method="GET",
                origin=origin,
                headers={
                    "Upgrade": "websocket",
                    "Connection": "Upgrade",
                    "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",
                    "Sec-WebSocket-Version": "13"
                }
            )
            
            websocket_results.append({
                "origin": origin,
                "upgrade_attempted": True,
                "cors_headers_present": "Access-Control-Allow-Origin" in result.headers,
                "response_time": result.response_time,
                "status_code": result.status_code
            })
        
        return websocket_results
    
    async def _test_multiple_origins(self) -> List[Dict[str, Any]]:
        """Test multiple origin validation scenarios."""
        multi_origin_results = []
        
        # Test allowed origins
        allowed_origins = [
            "http://localhost:3001",
            "http://127.0.0.1:3001",
            "https://app.netrasystems.ai"
        ]
        
        # Test blocked origins
        blocked_origins = [
            "https://malicious.com",
            "http://evil.example.com",
            "https://not-allowed.netrasystems.ai"
        ]
        
        for origin in allowed_origins:
            result = await self._make_cors_request(
                f"{self.auth_service_url}/auth/config",
                method="GET",
                origin=origin
            )
            
            multi_origin_results.append({
                "origin": origin,
                "expected_allowed": True,
                "actually_allowed": result.headers.get("Access-Control-Allow-Origin") is not None,
                "response_time": result.response_time
            })
        
        for origin in blocked_origins:
            result = await self._make_cors_request(
                f"{self.auth_service_url}/auth/config",
                method="GET",
                origin=origin
            )
            
            multi_origin_results.append({
                "origin": origin,
                "expected_allowed": False,
                "actually_allowed": result.headers.get("Access-Control-Allow-Origin") is not None,
                "response_time": result.response_time
            })
        
        return multi_origin_results
    
    async def _make_cors_request(self, url: str, method: str = "GET", 
                               origin: str = "", headers: Optional[Dict[str, str]] = None) -> CorsTestResult:
        """Make CORS request and return structured result."""
        request_headers = headers or {}
        if origin:
            request_headers["Origin"] = origin
        
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await getattr(client, method.lower())(url, headers=request_headers)
                response_time = time.time() - start_time
                
                return CorsTestResult(
                    endpoint=url,
                    origin=origin,
                    method=method,
                    preflight_success=method == "OPTIONS" and response.status_code == 200,
                    actual_success=response.status_code < 400,
                    headers=dict(response.headers),
                    response_time=response_time,
                    status_code=response.status_code
                )
                
        except Exception as e:
            return CorsTestResult(
                endpoint=url,
                origin=origin,
                method=method,
                preflight_success=False,
                actual_success=False,
                headers={},
                response_time=time.time() - start_time,
                status_code=500
            )
    
    def _has_required_cors_headers(self, headers: Dict[str, str]) -> bool:
        """Check if response has required CORS headers."""
        required_headers = [
            "Access-Control-Allow-Origin",
            "Access-Control-Allow-Methods",
            "Access-Control-Allow-Headers"
        ]
        return all(header in headers for header in required_headers)
    
    async def validate_critical_path_results(self, results: Dict[str, Any]) -> bool:
        """Validate CORS auth service test results."""
        validation_checks = []
        
        # Validate preflight requests
        preflight_success_rate = self._calculate_success_rate(results["preflight_tests"])
        validation_checks.append(preflight_success_rate >= 95.0)
        
        # Validate auth config endpoint
        auth_config_success_rate = self._calculate_success_rate(results["auth_config_tests"])
        validation_checks.append(auth_config_success_rate >= 95.0)
        
        # Validate multiple origin handling
        multi_origin_accuracy = self._validate_origin_filtering(results["multiple_origin_tests"])
        validation_checks.append(multi_origin_accuracy >= 95.0)
        
        # Validate response times
        avg_response_time = self._calculate_average_response_time(results)
        validation_checks.append(avg_response_time < 2.0)  # Under 2 seconds
        
        return all(validation_checks)
    
    def _calculate_success_rate(self, test_results: List[Dict[str, Any]]) -> float:
        """Calculate success rate percentage."""
        if not test_results:
            return 0.0
        
        successful = sum(1 for result in test_results if result.get("success", False))
        return (successful / len(test_results)) * 100.0
    
    def _validate_origin_filtering(self, multi_origin_results: List[Dict[str, Any]]) -> float:
        """Validate origin filtering accuracy."""
        if not multi_origin_results:
            return 0.0
        
        correct_filtering = sum(
            1 for result in multi_origin_results 
            if result["expected_allowed"] == result["actually_allowed"]
        )
        
        return (correct_filtering / len(multi_origin_results)) * 100.0
    
    def _calculate_average_response_time(self, results: Dict[str, Any]) -> float:
        """Calculate average response time across all tests."""
        all_response_times = []
        
        for test_category in results.values():
            if isinstance(test_category, list):
                for test_result in test_category:
                    if "response_time" in test_result:
                        all_response_times.append(test_result["response_time"])
        
        if not all_response_times:
            return 0.0
        
        return sum(all_response_times) / len(all_response_times)
    
    async def cleanup_test_specific_resources(self) -> None:
        """Cleanup Docker containers and test resources."""
        if self.docker_compose:
            try:
                self.docker_compose.stop()
            except Exception as e:
                print(f"Docker cleanup warning: {e}")

@pytest.fixture
async def cors_auth_l4_test():
    """Fixture for CORS auth service L4 test."""
    test_instance = CorsAuthServiceL4Test()
    try:
        yield test_instance
    finally:
        await test_instance.cleanup_l4_resources()

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.L4
async def test_cors_configuration_frontend_auth_service_l4(cors_auth_l4_test):
    """Test CORS configuration between Frontend and Auth Service (L4)."""
    # Run complete critical path test
    metrics = await cors_auth_l4_test.run_complete_critical_path_test()
    
    # Assert business requirements
    assert metrics.success, f"Critical path failed: {metrics.errors}"
    assert metrics.error_count == 0, f"Unexpected errors: {metrics.errors}"
    assert metrics.average_response_time < 2.0, f"Response time too slow: {metrics.average_response_time:.2f}s"
    assert metrics.success_rate >= 95.0, f"Success rate too low: {metrics.success_rate:.1f}%"
    
    # Validate specific CORS requirements
    test_results = metrics.details
    
    # All preflight requests should succeed for allowed origins
    preflight_tests = test_results.get("preflight_tests", [])
    assert len(preflight_tests) >= 3, "Insufficient preflight tests"
    
    successful_preflights = [t for t in preflight_tests if t["success"]]
    assert len(successful_preflights) >= 3, "Not enough successful preflight requests"
    
    # Auth config endpoint should return CORS headers
    auth_config_tests = test_results.get("auth_config_tests", [])
    cors_enabled_configs = [t for t in auth_config_tests if t["has_cors_headers"]]
    assert len(cors_enabled_configs) >= 3, "Auth config missing CORS headers"
    
    # Multiple origin validation should work correctly
    multi_origin_tests = test_results.get("multiple_origin_tests", [])
    correct_origin_handling = [
        t for t in multi_origin_tests 
        if t["expected_allowed"] == t["actually_allowed"]
    ]
    assert len(correct_origin_handling) >= len(multi_origin_tests) * 0.95, "Origin filtering accuracy too low"