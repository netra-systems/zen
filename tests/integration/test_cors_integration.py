#!/usr/bin/env python3
"""
CORS Integration Tests
Tests cross-origin requests between services and validates CORS headers in real scenarios.
"""

import os
import pytest
import asyncio
import httpx
import websockets
import json
from typing import Dict, Any, Optional
from unittest.mock import patch


class TestCORSCrossOriginRequests:
    """Test cross-origin requests between frontend and backend services."""
    
    @pytest.fixture
    def mock_backend_server_url(self):
        """Get backend server URL for testing."""
        return os.getenv("BACKEND_URL", "http://localhost:8000")
    
    @pytest.fixture  
    def mock_auth_server_url(self):
        """Get auth server URL for testing."""
        return os.getenv("AUTH_URL", "http://localhost:8081")
    
    @pytest.fixture
    def frontend_origin(self):
        """Frontend origin that makes cross-origin requests."""
        return "http://localhost:3001"
    
    @pytest.mark.asyncio
    async def test_frontend_to_backend_cors(self, mock_backend_server_url, frontend_origin):
        """Test cross-origin request from frontend (3001) to backend (8000)."""
        async with httpx.AsyncClient() as client:
            headers = {
                "Origin": frontend_origin,
                "Content-Type": "application/json"
            }
            
            try:
                # Test OPTIONS preflight request
                response = await client.options(
                    f"{mock_backend_server_url}/health",
                    headers=headers,
                    timeout=5.0
                )
                
                # Verify preflight response
                assert response.status_code == 200
                assert response.headers.get("Access-Control-Allow-Origin") == frontend_origin
                assert response.headers.get("Access-Control-Allow-Credentials") == "true"
                assert "GET" in response.headers.get("Access-Control-Allow-Methods", "")
                assert "OPTIONS" in response.headers.get("Access-Control-Allow-Methods", "")
                
                # Test actual GET request
                response = await client.get(
                    f"{mock_backend_server_url}/health",
                    headers=headers,
                    timeout=5.0
                )
                
                # Verify GET response has CORS headers
                assert response.status_code == 200
                assert response.headers.get("Access-Control-Allow-Origin") == frontend_origin
                assert response.headers.get("Access-Control-Allow-Credentials") == "true"
                
            except httpx.ConnectError:
                pytest.skip("Backend server not available for integration test")
            except asyncio.TimeoutError:
                pytest.skip("Backend server timeout - service may not be running")
    
    @pytest.mark.asyncio
    async def test_frontend_to_auth_service_cors(self, mock_auth_server_url, frontend_origin):
        """Test cross-origin request from frontend (3001) to auth service (8081)."""
        async with httpx.AsyncClient() as client:
            headers = {
                "Origin": frontend_origin,
                "Content-Type": "application/json"
            }
            
            try:
                # Test the specific regression case: /auth/config endpoint
                response = await client.options(
                    f"{mock_auth_server_url}/auth/config",
                    headers=headers,
                    timeout=5.0
                )
                
                # This should NOT fail with CORS policy error
                assert response.status_code == 200
                assert response.headers.get("Access-Control-Allow-Origin") == frontend_origin
                assert response.headers.get("Access-Control-Allow-Credentials") == "true"
                
                # Test actual GET request to /auth/config
                response = await client.get(
                    f"{mock_auth_server_url}/auth/config",
                    headers=headers,
                    timeout=5.0
                )
                
                # Verify response has CORS headers
                assert response.headers.get("Access-Control-Allow-Origin") == frontend_origin
                assert response.headers.get("Access-Control-Allow-Credentials") == "true"
                
            except httpx.ConnectError:
                pytest.skip("Auth service not available for integration test")
            except asyncio.TimeoutError:
                pytest.skip("Auth service timeout - service may not be running")
    
    @pytest.mark.asyncio
    async def test_auth_service_health_endpoints_cors(self, mock_auth_server_url, frontend_origin):
        """Test CORS on auth service health endpoints."""
        async with httpx.AsyncClient() as client:
            headers = {"Origin": frontend_origin}
            
            endpoints_to_test = ["/health", "/health/ready", "/"]
            
            for endpoint in endpoints_to_test:
                try:
                    # Test OPTIONS preflight
                    response = await client.options(
                        f"{mock_auth_server_url}{endpoint}",
                        headers=headers,
                        timeout=5.0
                    )
                    
                    assert response.status_code == 200, f"OPTIONS failed for {endpoint}"
                    assert response.headers.get("Access-Control-Allow-Origin") == frontend_origin
                    
                    # Test GET request
                    response = await client.get(
                        f"{mock_auth_server_url}{endpoint}",
                        headers=headers,
                        timeout=5.0
                    )
                    
                    assert response.headers.get("Access-Control-Allow-Origin") == frontend_origin
                    
                except httpx.ConnectError:
                    pytest.skip(f"Auth service not available for {endpoint}")
                except asyncio.TimeoutError:
                    pytest.skip(f"Auth service timeout for {endpoint}")
    
    @pytest.mark.asyncio
    async def test_multiple_origin_validation(self, mock_backend_server_url):
        """Test CORS validation with different origins."""
        async with httpx.AsyncClient() as client:
            test_cases = [
                ("http://localhost:3000", True),
                ("http://localhost:3001", True),
                ("http://127.0.0.1:3000", True),
                ("https://staging.netrasystems.ai", True),  # Should work in staging/dev
                ("https://malicious.com", False),
            ]
            
            for origin, should_allow in test_cases:
                headers = {"Origin": origin}
                
                try:
                    response = await client.options(
                        f"{mock_backend_server_url}/health",
                        headers=headers,
                        timeout=5.0
                    )
                    
                    if should_allow:
                        # Should have CORS headers for allowed origins
                        assert response.status_code == 200
                        cors_origin = response.headers.get("Access-Control-Allow-Origin")
                        assert cors_origin == origin or cors_origin == "*"
                    else:
                        # Should either reject or not include origin in response
                        cors_origin = response.headers.get("Access-Control-Allow-Origin")
                        if cors_origin:
                            # If CORS headers are present, they should not match the malicious origin
                            assert cors_origin != origin
                    
                except httpx.ConnectError:
                    pytest.skip("Backend server not available for origin validation test")
                except asyncio.TimeoutError:
                    pytest.skip("Backend server timeout during origin validation")


class TestCORSWebSocketIntegration:
    """Test CORS with WebSocket connections."""
    
    @pytest.fixture
    def websocket_url(self):
        """Get WebSocket URL for testing."""
        return os.getenv("WS_URL", "ws://localhost:8000/ws")
    
    @pytest.mark.asyncio
    async def test_websocket_cors_connection(self, websocket_url):
        """Test WebSocket connection with CORS origin header."""
        origin = "http://localhost:3001"
        
        try:
            # WebSocket connection with origin header
            async with websockets.connect(
                websocket_url,
                extra_headers={"Origin": origin},
                timeout=5.0
            ) as websocket:
                # If connection succeeds, CORS is working
                assert websocket.open
                
                # Try to send a ping
                await websocket.ping()
                
        except (websockets.exceptions.ConnectionClosed, 
                websockets.exceptions.InvalidURI,
                ConnectionRefusedError,
                OSError):
            pytest.skip("WebSocket server not available for integration test")
        except asyncio.TimeoutError:
            pytest.skip("WebSocket connection timeout")
    
    @pytest.mark.asyncio
    async def test_websocket_cors_different_origins(self, websocket_url):
        """Test WebSocket CORS with different origins."""
        test_origins = [
            "http://localhost:3000",
            "http://localhost:3001", 
            "http://127.0.0.1:3000"
        ]
        
        for origin in test_origins:
            try:
                async with websockets.connect(
                    websocket_url,
                    extra_headers={"Origin": origin},
                    timeout=3.0
                ) as websocket:
                    assert websocket.open
                    
            except (websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.InvalidURI,
                    ConnectionRefusedError,
                    OSError):
                pytest.skip(f"WebSocket server not available for origin {origin}")
            except asyncio.TimeoutError:
                pytest.skip(f"WebSocket timeout for origin {origin}")


class TestCORSPreflightRequests:
    """Test OPTIONS preflight requests comprehensively."""
    
    @pytest.fixture
    def backend_url(self):
        return os.getenv("BACKEND_URL", "http://localhost:8000")
    
    @pytest.fixture
    def auth_url(self):
        return os.getenv("AUTH_URL", "http://localhost:8081")
    
    @pytest.mark.asyncio
    async def test_preflight_all_required_headers(self, backend_url):
        """Test that preflight responses include all required headers."""
        async with httpx.AsyncClient() as client:
            headers = {
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization, Content-Type"
            }
            
            try:
                response = await client.options(
                    f"{backend_url}/health",
                    headers=headers,
                    timeout=5.0
                )
                
                required_cors_headers = [
                    "Access-Control-Allow-Origin",
                    "Access-Control-Allow-Methods", 
                    "Access-Control-Allow-Headers",
                    "Access-Control-Allow-Credentials",
                    "Access-Control-Max-Age"
                ]
                
                for header in required_cors_headers:
                    assert header in response.headers, f"Missing required CORS header: {header}"
                
                # Verify specific values
                assert response.headers["Access-Control-Allow-Credentials"] == "true"
                assert int(response.headers["Access-Control-Max-Age"]) > 0
                
            except httpx.ConnectError:
                pytest.skip("Backend server not available for preflight test")
            except asyncio.TimeoutError:
                pytest.skip("Backend server timeout during preflight test")
    
    @pytest.mark.asyncio
    async def test_preflight_all_http_methods(self, backend_url):
        """Test preflight for all supported HTTP methods."""
        methods_to_test = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]
        
        async with httpx.AsyncClient() as client:
            for method in methods_to_test:
                headers = {
                    "Origin": "http://localhost:3001",
                    "Access-Control-Request-Method": method
                }
                
                try:
                    response = await client.options(
                        f"{backend_url}/health",
                        headers=headers,
                        timeout=5.0
                    )
                    
                    assert response.status_code == 200
                    allowed_methods = response.headers.get("Access-Control-Allow-Methods", "")
                    assert method in allowed_methods, f"Method {method} not in allowed methods: {allowed_methods}"
                    
                except httpx.ConnectError:
                    pytest.skip(f"Backend server not available for {method} preflight test")
                except asyncio.TimeoutError:
                    pytest.skip(f"Backend server timeout for {method} preflight test")
    
    @pytest.mark.asyncio
    async def test_preflight_required_headers_allowed(self, auth_url):
        """Test that all required headers are allowed in preflight."""
        required_headers = [
            "Authorization",
            "Content-Type", 
            "X-Request-ID",
            "X-Trace-ID",
            "Accept",
            "Origin",
            "Referer",
            "X-Requested-With"
        ]
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": ", ".join(required_headers)
            }
            
            try:
                response = await client.options(
                    f"{auth_url}/auth/config",
                    headers=headers,
                    timeout=5.0
                )
                
                assert response.status_code == 200
                allowed_headers = response.headers.get("Access-Control-Allow-Headers", "")
                
                for header in required_headers:
                    assert header in allowed_headers, f"Header {header} not in allowed headers: {allowed_headers}"
                    
            except httpx.ConnectError:
                pytest.skip("Auth service not available for headers preflight test")
            except asyncio.TimeoutError:
                pytest.skip("Auth service timeout during headers preflight test")


class TestCORSEnvironmentSpecificBehavior:
    """Test CORS behavior specific to different environments."""
    
    @pytest.mark.asyncio
    async def test_development_wildcard_behavior(self):
        """Test development environment allows wildcard origins."""
        # This test validates that development environment properly handles wildcard CORS
        with patch.dict(os.environ, {"ENVIRONMENT": "development", "CORS_ORIGINS": "*"}):
            from app.core.middleware_setup import get_cors_origins, is_origin_allowed
            
            origins = get_cors_origins()
            
            # Development should allow various localhost origins
            test_origins = [
                "http://localhost:3000",
                "http://localhost:3001", 
                "http://localhost:8000",
                "http://127.0.0.1:5000",
                "https://localhost:8080"
            ]
            
            for origin in test_origins:
                assert is_origin_allowed(origin, origins), f"Development should allow {origin}"
    
    @pytest.mark.asyncio 
    async def test_staging_pattern_matching(self):
        """Test staging environment pattern matching."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging", "CORS_ORIGINS": ""}):
            from app.core.middleware_setup import get_cors_origins, is_origin_allowed
            
            origins = get_cors_origins()
            
            # Staging should allow specific patterns
            allowed_origins = [
                "https://staging.netrasystems.ai",
                "https://app.staging.netrasystems.ai",
                "https://pr-123.staging.netrasystems.ai",
                "https://netra-frontend-abc123.us-central1.run.app",
                "http://localhost:3000"
            ]
            
            disallowed_origins = [
                "https://malicious.com",
                "https://app.netrasystems.ai",  # Production domain
                "https://fake.staging.evil.com"
            ]
            
            for origin in allowed_origins:
                assert is_origin_allowed(origin, origins), f"Staging should allow {origin}"
                
            for origin in disallowed_origins:
                assert not is_origin_allowed(origin, origins), f"Staging should not allow {origin}"


class TestCORSRegressionScenarios:
    """Test specific regression scenarios identified in the CORS specification."""
    
    @pytest.mark.asyncio
    async def test_auth_config_endpoint_regression(self):
        """Test the specific regression: frontend (3001) -> auth service (8081) /auth/config."""
        auth_url = os.getenv("AUTH_URL", "http://localhost:8081")
        frontend_origin = "http://localhost:3001"
        
        async with httpx.AsyncClient() as client:
            headers = {"Origin": frontend_origin}
            
            try:
                # This specific request was failing before the CORS fix
                response = await client.get(
                    f"{auth_url}/auth/config",
                    headers=headers,
                    timeout=5.0
                )
                
                # Should NOT get CORS policy error
                # Should have proper CORS headers
                cors_origin = response.headers.get("Access-Control-Allow-Origin")
                assert cors_origin in [frontend_origin, "*"], "Auth config endpoint should allow frontend origin"
                
            except httpx.ConnectError:
                pytest.skip("Auth service not available for regression test")
            except asyncio.TimeoutError:
                pytest.skip("Auth service timeout during regression test")
    
    @pytest.mark.asyncio
    async def test_credentials_with_wildcard_regression(self):
        """Test that credentials work properly with wildcard origins."""
        # The regression was that credentials: true cannot be used with origin: "*"
        # Our solution uses DynamicCORSMiddleware to echo back the requesting origin
        
        backend_url = os.getenv("BACKEND_URL", "http://localhost:8000")
        
        async with httpx.AsyncClient() as client:
            headers = {
                "Origin": "http://localhost:3001",
                "Cookie": "test-session=abc123"  # Simulate credential request
            }
            
            try:
                response = await client.get(
                    f"{backend_url}/health",
                    headers=headers,
                    timeout=5.0
                )
                
                # Should work with credentials
                cors_origin = response.headers.get("Access-Control-Allow-Origin")
                cors_credentials = response.headers.get("Access-Control-Allow-Credentials")
                
                # Should either echo back the origin or be wildcard (but not both)
                assert cors_origin is not None, "CORS origin header should be present"
                assert cors_credentials == "true", "CORS credentials should be allowed"
                
                # If using wildcard, should be handled by DynamicCORSMiddleware
                if cors_origin == "*":
                    # This would be a problem with credentials, so should not happen
                    assert cors_credentials != "true", "Cannot use credentials with wildcard origin"
                
            except httpx.ConnectError:
                pytest.skip("Backend server not available for credentials test")
            except asyncio.TimeoutError:
                pytest.skip("Backend server timeout during credentials test")
    
    @pytest.mark.asyncio
    async def test_port_mismatch_regression(self):
        """Test that port mismatches don't cause CORS failures."""
        # Regression: Auth service running on unexpected port
        
        # Test various port combinations that should work in development
        port_combinations = [
            ("http://localhost:3000", "http://localhost:8000"),  # Frontend -> Backend
            ("http://localhost:3001", "http://localhost:8000"),  # Alt Frontend -> Backend  
            ("http://localhost:3000", "http://localhost:8081"),  # Frontend -> Auth
            ("http://localhost:3001", "http://localhost:8081"),  # Alt Frontend -> Auth
        ]
        
        for frontend_origin, backend_url in port_combinations:
            async with httpx.AsyncClient() as client:
                headers = {"Origin": frontend_origin}
                
                try:
                    response = await client.options(
                        f"{backend_url}/health",
                        headers=headers,
                        timeout=3.0
                    )
                    
                    # Should work for all localhost port combinations in development
                    assert response.status_code == 200
                    cors_origin = response.headers.get("Access-Control-Allow-Origin")
                    assert cors_origin in [frontend_origin, "*"], f"Port combination should work: {frontend_origin} -> {backend_url}"
                    
                except (httpx.ConnectError, asyncio.TimeoutError):
                    # Skip if service not available, but don't fail the test
                    pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])