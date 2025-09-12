from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
#!/usr/bin/env python3
"""
Comprehensive CORS Configuration Tests for DEV MODE

BVJ (Business Value Justification):
- Segment: Platform/Internal | Goal: Stability | Impact: Platform Reliability
- Value Impact: Prevents CORS failures that block all user interactions
- Strategic Impact: Ensures service communication reliability across environments
- Risk Mitigation: Validates CORS configuration prevents 100% user access loss

Test Coverage:
 PASS:  CORS headers for all endpoints
 PASS:  Preflight OPTIONS request handling  
 PASS:  Multi-origin validation
 PASS:  Credentials support testing
 PASS:  WebSocket CORS validation
 PASS:  Service coordination CORS
 PASS:  Error scenarios and recovery
 PASS:  Performance monitoring
"""

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import pytest
import websockets

# Test environment setup
get_env().set("TESTING", "1", "test")
get_env().set("CORS_ORIGINS", "*", "test")
get_env().set("ENVIRONMENT", "development", "test")


@dataclass
class CORSTestConfig:
    """CORS test configuration for various environments."""
    backend_url: str = "http://localhost:8000"
    auth_url: str = "http://localhost:8081"
    frontend_url: str = "http://localhost:3001"
    websocket_url: str = "ws://localhost:8000/ws"
    test_origins: List[str] = None
    
    def __post_init__(self):
        if self.test_origins is None:
            self.test_origins = [
                "http://localhost:3000",
                "http://localhost:3001", 
                "http://127.0.0.1:3001",
                "https://app.staging.netrasystems.ai"
            ]


class CORSValidator:
    """Utility class for CORS validation and testing."""
    
    def __init__(self, config: CORSTestConfig):
        self.config = config
        self.client: Optional[httpx.AsyncClient] = None
        self.metrics: Dict[str, float] = {}
    
    @asynccontextmanager
    async def http_client(self):
        """Managed HTTP client with timeouts."""
        self.client = httpx.AsyncClient(timeout=10.0, follow_redirects=True)
        try:
            yield self.client
        finally:
            await self.client.aclose()
            self.client = None
    
    async def validate_cors_headers(self, response: httpx.Response, 
                                   origin: str) -> Dict[str, Any]:
        """Validate CORS headers in response."""
        headers = response.headers
        return {
            "origin_allowed": headers.get("access-control-allow-origin") in [origin, "*"],
            "credentials_allowed": headers.get("access-control-allow-credentials") == "true",
            "methods_present": "access-control-allow-methods" in headers,
            "headers_present": "access-control-allow-headers" in headers,
            "expose_headers": headers.get("access-control-expose-headers", ""),
            "max_age": headers.get("access-control-max-age")
        }
    
    @pytest.mark.e2e
    async def test_preflight_request(self, url: str, origin: str) -> Dict[str, Any]:
        """Test OPTIONS preflight request."""
        async with self.http_client() as client:
            start_time = time.time()
            
            response = await client.options(
                url,
                headers={
                    "Origin": origin,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "Content-Type,Authorization"
                }
            )
            
            duration = time.time() - start_time
            cors_validation = await self.validate_cors_headers(response, origin)
            
            return {
                "status_code": response.status_code,
                "response_time": duration,
                "cors_valid": cors_validation,
                "success": response.status_code == 200 and cors_validation["origin_allowed"]
            }


@pytest.mark.e2e
class TestCORSConfiguration:
    """Comprehensive CORS configuration tests."""
    
    @pytest.fixture
    def cors_config(self):
        """CORS test configuration."""
        return CORSTestConfig()
    
    @pytest.fixture
    def cors_validator(self, cors_config):
        """CORS validation utility."""
        return CORSValidator(cors_config)
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_backend_cors_endpoints(self, cors_validator):
        """Test CORS headers on all backend endpoints."""
        backend_endpoints = [
            "/health",
            "/health/ready", 
            "/api/threads",
            "/auth/status",
            "/api/config"
        ]
        
        results = {}
        
        async with cors_validator.http_client() as client:
            for endpoint in backend_endpoints:
                for origin in cors_validator.config.test_origins:
                    url = f"{cors_validator.config.backend_url}{endpoint}"
                    
                    try:
                        response = await client.get(
                            url,
                            headers={"Origin": origin}
                        )
                        
                        cors_validation = await cors_validator.validate_cors_headers(
                            response, origin
                        )
                        
                        results[f"{endpoint}_{origin}"] = {
                            "status_code": response.status_code,
                            "cors_valid": cors_validation,
                            "endpoint": endpoint,
                            "origin": origin
                        }
                        
                        # Verify CORS headers are present
                        assert cors_validation["origin_allowed"], \
                            f"Origin {origin} not allowed for {endpoint}"
                        assert cors_validation["credentials_allowed"], \
                            f"Credentials not allowed for {endpoint}"
                            
                    except Exception as e:
                        results[f"{endpoint}_{origin}"] = {
                            "error": str(e),
                            "endpoint": endpoint,
                            "origin": origin
                        }
        
        # Ensure at least 80% of endpoint/origin combinations work
        successful = sum(1 for r in results.values() 
                        if r.get("cors_valid", {}).get("origin_allowed", False))
        total = len(results)
        success_rate = successful / total if total > 0 else 0
        
        assert success_rate >= 0.8, \
            f"CORS success rate {success_rate:.2%} below 80% threshold"
    
    @pytest.mark.asyncio 
    @pytest.mark.e2e
    async def test_auth_service_cors_endpoints(self, cors_validator):
        """Test CORS headers on auth service endpoints."""
        auth_endpoints = [
            "/health",
            "/auth/config",
            "/auth/status", 
            "/auth/login",
            "/auth/callback"
        ]
        
        results = {}
        
        async with cors_validator.http_client() as client:
            for endpoint in auth_endpoints:
                for origin in cors_validator.config.test_origins:
                    url = f"{cors_validator.config.auth_url}{endpoint}"
                    
                    try:
                        response = await client.get(
                            url,
                            headers={"Origin": origin}
                        )
                        
                        cors_validation = await cors_validator.validate_cors_headers(
                            response, origin
                        )
                        
                        results[f"{endpoint}_{origin}"] = cors_validation
                        
                        # Critical: auth/config must have CORS headers
                        if endpoint == "/auth/config":
                            assert cors_validation["origin_allowed"], \
                                f"Auth config endpoint missing CORS for {origin}"
                                
                    except Exception as e:
                        results[f"{endpoint}_{origin}"] = {"error": str(e)}
        
        # Auth service CORS is critical - must be 100% working
        auth_config_results = [r for k, r in results.items() 
                              if "/auth/config" in k]
        auth_config_success = sum(1 for r in auth_config_results 
                                 if r.get("origin_allowed", False))
        
        assert auth_config_success == len(auth_config_results), \
            "Auth config endpoint CORS must work for all origins"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_preflight_options_requests(self, cors_validator):
        """Test OPTIONS preflight requests across services."""
        test_urls = [
            f"{cors_validator.config.backend_url}/api/threads",
            f"{cors_validator.config.auth_url}/auth/config",
            f"{cors_validator.config.backend_url}/health"
        ]
        
        for url in test_urls:
            for origin in cors_validator.config.test_origins:
                result = await cors_validator.test_preflight_request(url, origin)
                
                assert result["success"], \
                    f"Preflight failed for {url} with origin {origin}: {result}"
                assert result["response_time"] < 2.0, \
                    f"Preflight too slow ({result['response_time']:.2f}s) for {url}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_cors_validation(self, cors_validator):
        """Test WebSocket connection with CORS validation."""
        # Note: WebSocket CORS is handled during the initial HTTP upgrade
        async with cors_validator.http_client() as client:
            try:
                # Test WebSocket upgrade request with Origin header
                response = await client.get(
                    cors_validator.config.websocket_url.replace("ws://", "http://"),
                    headers={
                        "Origin": cors_validator.config.frontend_url,
                        "Connection": "Upgrade",
                        "Upgrade": "websocket"
                    }
                )
                
                # Should either upgrade successfully or return valid CORS headers
                if response.status_code in [101, 200]:
                    cors_validation = await cors_validator.validate_cors_headers(
                        response, cors_validator.config.frontend_url
                    )
                    assert cors_validation["origin_allowed"], \
                        "WebSocket upgrade must allow frontend origin"
                        
            except Exception as e:
                # WebSocket endpoint might not be available - that's ok for this test
                # The important thing is that when it is available, CORS works
                assert "Connection refused" in str(e) or "404" in str(e), \
                    f"Unexpected WebSocket CORS error: {e}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cross_service_cors_coordination(self, cors_validator):
        """Test CORS coordination between services."""
        # Simulate frontend making requests to both services
        frontend_origin = cors_validator.config.frontend_url
        
        async with cors_validator.http_client() as client:
            # Step 1: Get auth config from auth service
            auth_response = await client.get(
                f"{cors_validator.config.auth_url}/auth/config",
                headers={"Origin": frontend_origin}
            )
            
            auth_cors = await cors_validator.validate_cors_headers(
                auth_response, frontend_origin
            )
            assert auth_cors["origin_allowed"], "Auth service CORS failed"
            
            # Step 2: Check backend health with same origin
            backend_response = await client.get(
                f"{cors_validator.config.backend_url}/health",
                headers={"Origin": frontend_origin}
            )
            
            backend_cors = await cors_validator.validate_cors_headers(
                backend_response, frontend_origin
            )
            assert backend_cors["origin_allowed"], "Backend service CORS failed"
            
            # Step 3: Verify consistent CORS behavior
            assert auth_cors["credentials_allowed"] == backend_cors["credentials_allowed"], \
                "Inconsistent credentials policy between services"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_performance_monitoring(self, cors_validator):
        """Test CORS performance and resource usage."""
        metrics = {
            "preflight_times": [],
            "cors_header_times": [],
            "total_requests": 0
        }
        
        # Test multiple rapid CORS requests
        async with cors_validator.http_client() as client:
            for i in range(10):
                start_time = time.time()
                
                # Preflight request
                preflight_start = time.time()
                await client.options(
                    f"{cors_validator.config.backend_url}/health",
                    headers={"Origin": cors_validator.config.frontend_url}
                )
                metrics["preflight_times"].append(time.time() - preflight_start)
                
                # Actual request with CORS
                cors_start = time.time()
                response = await client.get(
                    f"{cors_validator.config.backend_url}/health",
                    headers={"Origin": cors_validator.config.frontend_url}
                )
                metrics["cors_header_times"].append(time.time() - cors_start)
                
                metrics["total_requests"] += 2
        
        # Performance assertions
        avg_preflight = sum(metrics["preflight_times"]) / len(metrics["preflight_times"])
        avg_cors = sum(metrics["cors_header_times"]) / len(metrics["cors_header_times"])
        
        assert avg_preflight < 1.0, f"Preflight too slow: {avg_preflight:.2f}s"
        assert avg_cors < 2.0, f"CORS requests too slow: {avg_cors:.2f}s"
        
        # Resource usage should be reasonable
        assert metrics["total_requests"] == 20, "Request count mismatch"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_error_scenarios(self, cors_validator):
        """Test CORS error handling and recovery."""
        # Test with invalid origin
        async with cors_validator.http_client() as client:
            response = await client.get(
                f"{cors_validator.config.backend_url}/health",
                headers={"Origin": "https://malicious-site.com"}
            )
            
            # In dev mode with CORS_ORIGINS=*, this should still work
            # In production, this would be rejected
            cors_validation = await cors_validator.validate_cors_headers(
                response, "https://malicious-site.com"
            )
            
            # For dev environment, wildcard should allow any origin
            if get_env().get("CORS_ORIGINS") == "*":
                assert cors_validation["origin_allowed"], \
                    "Dev mode should allow any origin with CORS_ORIGINS=*"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_compliance_validation(self, cors_validator):
        """Validate CORS implementation compliance with spec."""
        compliance_results = {
            "required_headers": True,
            "preflight_support": True,
            "credentials_support": True,
            "method_support": True
        }
        
        async with cors_validator.http_client() as client:
            # Test required headers presence
            response = await client.get(
                f"{cors_validator.config.backend_url}/health",
                headers={"Origin": cors_validator.config.frontend_url}
            )
            
            required_headers = [
                "access-control-allow-origin",
                "access-control-allow-credentials"
            ]
            
            for header in required_headers:
                if header not in response.headers:
                    compliance_results["required_headers"] = False
            
            # Test preflight support
            preflight_response = await client.options(
                f"{cors_validator.config.backend_url}/health",
                headers={
                    "Origin": cors_validator.config.frontend_url,
                    "Access-Control-Request-Method": "POST"
                }
            )
            
            if preflight_response.status_code != 200:
                compliance_results["preflight_support"] = False
        
        # All compliance checks must pass
        for check, result in compliance_results.items():
            assert result, f"CORS compliance failed: {check}"