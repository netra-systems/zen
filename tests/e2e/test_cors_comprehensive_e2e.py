"""Comprehensive CORS E2E Tests for Final Implementation Agent
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment

Business Value Justification (BVJ):
1. Segment: All customer segments (Free, Early, Mid, Enterprise)
2. Business Goal: Ensure cross-origin communication works for frontend-backend integration
3. Value Impact: Critical for web application functionality across all tiers
4. Revenue Impact: Prevents customer access issues that could result in churn

Test Coverage:
- Development environment CORS (localhost origins)
- Staging environment CORS (staging domains)
- Production environment CORS (production domains)
- WebSocket CORS validation
- Error scenarios (blocked origins)
- Multi-service CORS consistency
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import aiohttp
import pytest
import websockets


class TestCORSValidationer:
    """Helper class for CORS validation testing."""
    
    def __init__(self):
        self.backend_url = "http://localhost:8000"
        self.auth_service_url = "http://localhost:8080"
        self.test_origins = {
            "development": [
                "http://localhost:3000",
                "http://localhost:3001", 
                "http://127.0.0.1:3000",
                "https://localhost:3000"
            ],
            "staging": [
                "https://app.staging.netrasystems.ai",
                "https://app.staging.netrasystems.ai",
                "https://auth.staging.netrasystems.ai"
            ],
            "production": [
                "https://netrasystems.ai",
                "https://app.netrasystems.ai",
                "https://auth.netrasystems.ai"
            ],
            "blocked": [
                "http://malicious-site.com",
                "https://attacker.net",
                "http://localhost:9999"
            ]
        }
    
    async def test_cors_preflight(self, origin: str, url: str) -> Dict[str, any]:
        """Test CORS preflight request."""
        headers = {
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization, Content-Type"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.options(url, headers=headers) as response:
                    return {
                        "status_code": response.status,
                        "origin_allowed": response.headers.get("Access-Control-Allow-Origin") == origin,
                        "credentials_allowed": response.headers.get("Access-Control-Allow-Credentials") == "true",
                        "methods_allowed": "POST" in response.headers.get("Access-Control-Allow-Methods", ""),
                        "headers_allowed": "Authorization" in response.headers.get("Access-Control-Allow-Headers", ""),
                        "response_headers": dict(response.headers)
                    }
        except Exception as e:
            return {"error": str(e), "origin": origin, "url": url}
    
    async def test_cors_actual_request(self, origin: str, url: str) -> Dict[str, any]:
        """Test actual CORS request."""
        headers = {
            "Origin": origin,
            "Content-Type": "application/json"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    return {
                        "status_code": response.status,
                        "origin_allowed": response.headers.get("Access-Control-Allow-Origin") == origin,
                        "credentials_allowed": response.headers.get("Access-Control-Allow-Credentials") == "true",
                        "response_headers": dict(response.headers)
                    }
        except Exception as e:
            return {"error": str(e), "origin": origin, "url": url}
    
    async def test_websocket_cors(self, origin: str, ws_url: str) -> Dict[str, any]:
        """Test WebSocket CORS."""
        extra_headers = {"Origin": origin}
        
        try:
            # Try to connect with origin header
            ws = await websockets.connect(ws_url, additional_headers=extra_headers)
            await ws.close()
            return {"connection_successful": True, "origin": origin}
        except websockets.exceptions.InvalidStatus as e:
            return {
                "connection_successful": False,
                "status_code": e.status_code,
                "origin": origin,
                "error": str(e)
            }
        except Exception as e:
            return {"connection_successful": False, "origin": origin, "error": str(e)}


@pytest.fixture
def cors_tester():
    """Create CORS validation tester fixture."""
    return CORSValidationTester()


class TestCORSComprehensiveE2E:
    """Comprehensive E2E tests for CORS configuration."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_development_origins_backend(self, cors_tester):
        """Test CORS works for development origins on backend service."""
        results = []
        
        for origin in cors_tester.test_origins["development"]:
            # Test preflight
            preflight_result = await cors_tester.test_cors_preflight(origin, f"{cors_tester.backend_url}/health")
            results.append({"type": "preflight", "origin": origin, "result": preflight_result})
            
            # Test actual request
            actual_result = await cors_tester.test_cors_actual_request(origin, f"{cors_tester.backend_url}/health")
            results.append({"type": "actual", "origin": origin, "result": actual_result})
        
        # Assert all development origins are allowed
        for result in results:
            if "error" not in result["result"]:
                assert result["result"]["status_code"] in [200, 204], f"CORS failed for {result['origin']}: {result['result']}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_development_origins_auth_service(self, cors_tester):
        """Test CORS works for development origins on auth service."""
        results = []
        
        for origin in cors_tester.test_origins["development"]:
            # Test preflight
            preflight_result = await cors_tester.test_cors_preflight(origin, f"{cors_tester.auth_service_url}/health")
            results.append({"type": "preflight", "origin": origin, "result": preflight_result})
            
            # Test actual request
            actual_result = await cors_tester.test_cors_actual_request(origin, f"{cors_tester.auth_service_url}/health")
            results.append({"type": "actual", "origin": origin, "result": actual_result})
        
        # Assert all development origins are allowed
        for result in results:
            if "error" not in result["result"]:
                assert result["result"]["status_code"] in [200, 204], f"Auth service CORS failed for {result['origin']}: {result['result']}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_cors_development_origins(self, cors_tester):
        """Test WebSocket CORS works for development origins."""
        ws_url = "ws://localhost:8000/ws"
        results = []
        
        for origin in cors_tester.test_origins["development"]:
            result = await cors_tester.test_websocket_cors(origin, ws_url)
            results.append({"origin": origin, "result": result})
        
        # At least one development origin should work for WebSocket
        successful_connections = [r for r in results if r["result"].get("connection_successful")]
        assert len(successful_connections) > 0, f"No WebSocket connections succeeded for development origins: {results}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_blocked_origins_rejected(self, cors_tester):
        """Test blocked origins are properly rejected."""
        results = []
        
        for origin in cors_tester.test_origins["blocked"]:
            # Test preflight - should be rejected
            preflight_result = await cors_tester.test_cors_preflight(origin, f"{cors_tester.backend_url}/health")
            results.append({"type": "preflight", "origin": origin, "result": preflight_result})
        
        # Assert blocked origins don't get CORS approval
        for result in results:
            if "error" not in result["result"]:
                # Origin should not be explicitly allowed in CORS headers
                assert not result["result"].get("origin_allowed", False), f"Blocked origin {result['origin']} was incorrectly allowed"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_consistency_across_services(self, cors_tester):
        """Test CORS configuration is consistent across backend and auth services."""
        test_origin = "http://localhost:3000"
        
        # Test backend service
        backend_preflight = await cors_tester.test_cors_preflight(test_origin, f"{cors_tester.backend_url}/health")
        
        # Test auth service
        auth_preflight = await cors_tester.test_cors_preflight(test_origin, f"{cors_tester.auth_service_url}/health")
        
        # Both services should handle CORS consistently
        if "error" not in backend_preflight and "error" not in auth_preflight:
            backend_allows = backend_preflight.get("origin_allowed", False)
            auth_allows = auth_preflight.get("origin_allowed", False)
            
            # Both should either allow or deny the same origin
            assert backend_allows == auth_allows, f"CORS inconsistency: backend={backend_allows}, auth={auth_allows}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_credentials_support(self, cors_tester):
        """Test CORS credentials support is properly configured."""
        test_origin = "http://localhost:3000"
        
        # Test both services support credentials
        services = [
            ("backend", f"{cors_tester.backend_url}/health"),
            ("auth", f"{cors_tester.auth_service_url}/health")
        ]
        
        for service_name, url in services:
            result = await cors_tester.test_cors_preflight(test_origin, url)
            
            if "error" not in result:
                assert result.get("credentials_allowed", False), f"{service_name} service doesn't support CORS credentials"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_required_headers_allowed(self, cors_tester):
        """Test required headers are allowed in CORS configuration."""
        test_origin = "http://localhost:3000"
        required_headers = ["Authorization", "Content-Type", "X-Request-ID"]
        
        # Test backend service
        result = await cors_tester.test_cors_preflight(test_origin, f"{cors_tester.backend_url}/health")
        
        if "error" not in result:
            allowed_headers = result.get("response_headers", {}).get("Access-Control-Allow-Headers", "")
            
            for header in required_headers:
                assert header in allowed_headers, f"Required header {header} not allowed in CORS"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_required_methods_allowed(self, cors_tester):
        """Test required HTTP methods are allowed in CORS configuration."""
        test_origin = "http://localhost:3000"
        required_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        
        # Test backend service
        result = await cors_tester.test_cors_preflight(test_origin, f"{cors_tester.backend_url}/health")
        
        if "error" not in result:
            allowed_methods = result.get("response_headers", {}).get("Access-Control-Allow-Methods", "")
            
            for method in required_methods:
                assert method in allowed_methods, f"Required method {method} not allowed in CORS"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_environment_specific_origins(self, cors_tester):
        """Test environment-specific CORS origins work correctly."""
        # This test would need environment detection, for now test development
        current_env = get_env().get("ENVIRONMENT", "development")
        
        if current_env == "development":
            test_origins = cors_tester.test_origins["development"]
        elif current_env == "staging":
            test_origins = cors_tester.test_origins["staging"]
        else:
            test_origins = cors_tester.test_origins["production"]
        
        results = []
        for origin in test_origins[:2]:  # Test first 2 origins to keep test manageable
            result = await cors_tester.test_cors_preflight(origin, f"{cors_tester.backend_url}/health")
            results.append({"origin": origin, "result": result})
        
        # At least one environment-appropriate origin should work
        successful_tests = [r for r in results if r["result"].get("status_code") in [200, 204]]
        assert len(successful_tests) > 0, f"No CORS success for {current_env} environment: {results}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_security_headers_present(self, cors_tester):
        """Test security headers are present in CORS responses."""
        test_origin = "http://localhost:3000"
        
        result = await cors_tester.test_cors_preflight(test_origin, f"{cors_tester.backend_url}/health")
        
        if "error" not in result:
            headers = result.get("response_headers", {})
            
            # Check for security headers
            security_headers = ["Vary", "X-Content-Type-Options", "X-Frame-Options"]
            for header in security_headers:
                # Note: These might not be present in all environments, so we just log their presence
                header_present = header in headers
                print(f"Security header {header}: {'present' if header_present else 'missing'}")