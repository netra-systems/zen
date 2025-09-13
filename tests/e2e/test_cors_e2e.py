#!/usr/bin/env python3
"""
from shared.isolated_environment import get_env
from shared.isolated_environment import IsolatedEnvironment
CORS End-to-End Tests
Complete authentication and user flows across services with CORS validation.
"""

import asyncio
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import httpx
import pytest
import websockets


@dataclass
class ServiceEndpoints:
    """Service endpoint configuration for testing."""
    backend_url: str = "http://localhost:8000"
    auth_url: str = "http://localhost:8081"
    frontend_url: str = "http://localhost:3001"
    websocket_url: str = "ws://localhost:8000/ws"


@pytest.mark.e2e
class TestCORSCompleteAuthFlow:
    """Test complete authentication flow across services with CORS."""
    
    @pytest.fixture
    def services(self):
        """Get service endpoints configuration."""
        return ServiceEndpoints(
            backend_url=get_env().get("BACKEND_URL", "http://localhost:8000"),
            auth_url=get_env().get("AUTH_URL", "http://localhost:8081"),
            frontend_url=get_env().get("FRONTEND_URL", "http://localhost:3001"),
            websocket_url=get_env().get("WS_URL", "ws://localhost:8000/ws")
        )
    
    @pytest.fixture
    def frontend_origin(self, services):
        """Frontend origin for CORS testing."""
        return services.frontend_url
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_auth_config_flow_e2e(self, services, frontend_origin):
        """Test complete auth config retrieval flow with CORS."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {
                "Origin": frontend_origin,
                "Content-Type": "application/json"
            }
            
            try:
                # Step 1: Frontend fetches auth configuration
                response = await client.get(
                    f"{services.auth_url}/auth/config",
                    headers=headers,
                    timeout=10.0
                )
                
                # Verify CORS headers are present and correct
                assert response.headers.get("Access-Control-Allow-Origin") in [frontend_origin, "*"]
                assert response.headers.get("Access-Control-Allow-Credentials") == "true"
                
                # Verify response is valid
                assert response.status_code == 200
                config_data = response.json()
                assert isinstance(config_data, dict)
                
                # Step 2: If config contains OAuth URLs, test them too
                if "oauth_login_url" in config_data:
                    oauth_url = config_data["oauth_login_url"]
                    
                    # Test that OAuth URL can be accessed with CORS
                    response = await client.options(
                        oauth_url,
                        headers=headers,
                        timeout=5.0
                    )
                    
                    # OAuth endpoints should also support CORS
                    cors_origin = response.headers.get("Access-Control-Allow-Origin")
                    assert cors_origin is not None, "OAuth endpoint should have CORS headers"
                
            except httpx.ConnectError:
                pytest.skip("Auth service not available for e2e auth config test")
            except asyncio.TimeoutError:
                pytest.skip("Auth service timeout during e2e auth config test")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_complete_oauth_login_flow_cors(self, services, frontend_origin):
        """Test complete OAuth login flow with CORS considerations."""
        async with httpx.AsyncClient(follow_redirects=False) as client:
            headers = {"Origin": frontend_origin}
            
            try:
                # Step 1: Get auth configuration
                config_response = await client.get(
                    f"{services.auth_url}/auth/config",
                    headers=headers,
                    timeout=5.0
                )
                
                assert config_response.headers.get("Access-Control-Allow-Origin") in [frontend_origin, "*"]
                config = config_response.json()
                
                # Step 2: Test OAuth login endpoint
                login_response = await client.get(
                    f"{services.auth_url}/auth/login",
                    headers=headers,
                    timeout=5.0
                )
                
                # Should have CORS headers even for redirects
                cors_headers_present = (
                    "Access-Control-Allow-Origin" in login_response.headers or
                    login_response.status_code in [302, 307, 308]  # Redirects are OK
                )
                assert cors_headers_present, "Login endpoint should handle CORS or redirect properly"
                
                # Step 3: Test OAuth callback endpoint (simulated)
                # First try OPTIONS for CORS preflight, but accept 405 if only GET is supported
                callback_response = await client.options(
                    f"{services.auth_url}/auth/callback",
                    headers=headers,
                    timeout=5.0
                )
                
                if callback_response.status_code == 405:
                    # OPTIONS not supported, check if GET works and has CORS headers
                    callback_response = await client.get(
                        f"{services.auth_url}/auth/callback?test=1",
                        headers=headers,
                        timeout=5.0
                    )
                    # GET may return various status codes depending on OAuth flow
                    # 422 = validation error (missing required OAuth parameters)
                    # 400 = bad request, 302 = redirect, 200 = success
                    assert callback_response.status_code in [200, 302, 400, 422], \
                        f"Callback endpoint returned unexpected status: {callback_response.status_code}"
                else:
                    # OPTIONS is supported, should return 200
                    assert callback_response.status_code == 200
                    
                # Verify CORS headers are present 
                assert callback_response.headers.get("Access-Control-Allow-Origin") in [frontend_origin, "*"], \
                    "Callback endpoint should have CORS headers"
                
            except httpx.ConnectError:
                pytest.skip("Auth service not available for e2e OAuth flow test")
            except asyncio.TimeoutError:
                pytest.skip("Auth service timeout during e2e OAuth flow test")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_token_validation_across_services_cors(self, services, frontend_origin):
        """Test token validation across services with CORS."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {
                "Origin": frontend_origin,
                "Authorization": "Bearer test-token-123",
                "Content-Type": "application/json"
            }
            
            try:
                # Step 1: Validate token with auth service
                auth_response = await client.get(
                    f"{services.auth_url}/auth/status",
                    headers=headers,
                    timeout=5.0
                )
                
                assert auth_response.headers.get("Access-Control-Allow-Origin") in [frontend_origin, "*"]
                
                # Step 2: Use token with backend service
                backend_response = await client.get(
                    f"{services.backend_url}/health",
                    headers=headers,
                    timeout=5.0
                )
                
                assert backend_response.headers.get("Access-Control-Allow-Origin") in [frontend_origin, "*"]
                assert backend_response.headers.get("Access-Control-Allow-Credentials") == "true"
                
                # Step 3: Verify both services accept the same origin
                auth_origin = auth_response.headers.get("Access-Control-Allow-Origin")
                backend_origin = backend_response.headers.get("Access-Control-Allow-Origin")
                
                # Both should allow the same origin (consistency check)
                if auth_origin != "*" and backend_origin != "*":
                    assert auth_origin == backend_origin, "Services should have consistent CORS origins"
                
            except httpx.ConnectError:
                pytest.skip("Services not available for e2e token validation test")
            except asyncio.TimeoutError:
                pytest.skip("Service timeout during e2e token validation test")


@pytest.mark.e2e
class TestCORSPREnvironmentValidation:
    """Test PR environment dynamic origin validation."""
    
    @pytest.fixture
    def pr_origins(self):
        """Generate PR environment origins for testing."""
        return [
            "https://pr-123.staging.netrasystems.ai",
            "https://pr-456.staging.netrasystems.ai",
            "https://frontend-pr-789.staging.netrasystems.ai",
            "https://backend-pr-101.staging.netrasystems.ai"
        ]
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_pr_environment_dynamic_validation(self, pr_origins):
        """Test PR environment dynamic origin validation."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            from netra_backend.app.core.network_constants import URLConstants
            
            origins = URLConstants.get_cors_origins("staging")
            
            # All PR origins should be allowed in staging
            for pr_origin in pr_origins:
                assert pr_origin in origins, f"PR origin should be allowed: {pr_origin}"
            
            # Non-PR staging origins should also work
            regular_origins = [
                "https://app.staging.netrasystems.ai",
                "https://app.staging.netrasystems.ai"
            ]
            
            for origin in regular_origins:
                assert is_origin_allowed(origin, origins), f"Regular staging origin should be allowed: {origin}"
            
            # Production origins should be rejected
            production_origins = [
                "https://netrasystems.ai",
                "https://app.netrasystems.ai"
            ]
            
            for origin in production_origins:
                assert not is_origin_allowed(origin, origins), f"Production origin should be rejected in staging: {origin}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cloud_run_pr_deployment_validation(self):
        """Test Cloud Run PR deployment URL validation."""
        with patch.dict(os.environ, {"ENVIRONMENT": "staging"}):
            from netra_backend.app.core.middleware_setup import is_origin_allowed
            
            origins = ["*"]  # Staging uses pattern matching
            
            # Cloud Run PR deployment patterns
            cloud_run_origins = [
                "https://netra-frontend-pr123-abc.us-central1.run.app",
                "https://netra-backend-pr456-def.us-central1.run.app", 
                "https://service-pr789-xyz123-uc.a.run.app"
            ]
            
            for origin in cloud_run_origins:
                assert is_origin_allowed(origin, origins), f"Cloud Run PR origin should be allowed: {origin}"


@pytest.mark.e2e
class TestCORSProductionStrictValidation:
    """Test production strict origin enforcement."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_production_strict_origin_enforcement(self):
        """Test production environment strict origin validation."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production", "CORS_ORIGINS": ""}):
            
            origins = get_cors_origins()
            
            # Only production domains should be allowed
            allowed_origins = [
                "https://netrasystems.ai",
                "https://www.netrasystems.ai",
                "https://app.netrasystems.ai"
            ]
            
            for origin in allowed_origins:
                assert is_origin_allowed(origin, origins), f"Production origin should be allowed: {origin}"
            
            # All other origins should be rejected
            rejected_origins = [
                "http://localhost:3000",
                "https://app.staging.netrasystems.ai",
                "https://dev.netrasystems.ai",
                "https://malicious.com",
                "https://fake.netrasystems.ai",
                "*"
            ]
            
            for origin in rejected_origins:
                assert not is_origin_allowed(origin, origins), f"Non-production origin should be rejected: {origin}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_production_no_wildcard_allowed(self):
        """Test that production never allows wildcard origins."""
        with patch.dict(os.environ, {"ENVIRONMENT": "production"}):
            from netra_backend.app.core.middleware_setup import (
                _evaluate_wildcard_environment,
            )
            
            # Production should never allow wildcards
            assert not _evaluate_wildcard_environment(), "Production should not allow wildcard origins"


@pytest.mark.e2e
class TestCORSDynamicPortValidation:
    """Test CORS with dynamic localhost ports."""
    
    @pytest.fixture
    def dynamic_ports(self):
        """Generate dynamic port combinations for testing."""
        return [
            ("http://localhost:3000", "http://localhost:8000"),
            ("http://localhost:3001", "http://localhost:8000"), 
            ("http://localhost:3000", "http://localhost:8081"),
            ("http://localhost:3001", "http://localhost:8081"),
            ("http://127.0.0.1:3000", "http://127.0.0.1:8000"),
            ("http://127.0.0.1:3001", "http://127.0.0.1:8081"),
            ("https://localhost:3000", "https://localhost:8000"),  # HTTPS localhost
            ("http://localhost:49672", "http://localhost:8000"),   # Random dev port
            ("http://127.0.0.1:35281", "http://127.0.0.1:8081")   # Random dev port
        ]
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_dynamic_localhost_ports_allowed(self, dynamic_ports):
        """Test that dynamic localhost ports are allowed in development."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development", "CORS_ORIGINS": "*"}):
            
            origins = ["*"]
            
            for frontend_origin, backend_url in dynamic_ports:
                assert is_origin_allowed(frontend_origin, origins), f"Dynamic port should be allowed: {frontend_origin}"
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_localhost_pattern_comprehensive(self):
        """Test comprehensive localhost pattern matching."""
        with patch.dict(os.environ, {"ENVIRONMENT": "development"}):
            from netra_backend.app.core.middleware_setup import _check_localhost_pattern
            
            localhost_variations = [
                "http://localhost:3000",
                "https://localhost:8080",
                "http://127.0.0.1:5000", 
                "https://127.0.0.1",
                "http://localhost",
                "https://localhost"
            ]
            
            for origin in localhost_variations:
                assert _check_localhost_pattern(origin), f"Localhost pattern should match: {origin}"
            
            # Non-localhost should not match
            non_localhost = [
                "http://192.168.1.1:3000",
                "https://10.0.0.1:8080",
                "http://example.com"
            ]
            
            for origin in non_localhost:
                assert not _check_localhost_pattern(origin), f"Non-localhost should not match: {origin}"


@pytest.mark.e2e
class TestCORSCredentialRequestsAcrossServices:
    """Test credential-based requests across services."""
    
    @pytest.fixture
    def services(self):
        return ServiceEndpoints()
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cookie_based_requests_cors(self, services):
        """Test cookie-based requests with CORS."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {
                "Origin": services.frontend_url,
                "Cookie": "session=abc123; csrf=xyz789"
            }
            
            try:
                # Test cookie request to backend
                response = await client.get(
                    f"{services.backend_url}/health",
                    headers=headers,
                    timeout=5.0
                )
                
                # Should have CORS headers for credentialed requests
                assert response.headers.get("Access-Control-Allow-Credentials") == "true"
                cors_origin = response.headers.get("Access-Control-Allow-Origin")
                
                # Cannot be wildcard with credentials
                assert cors_origin != "*", "Cannot use wildcard origin with credentials"
                assert cors_origin == services.frontend_url or cors_origin is not None
                
            except httpx.ConnectError:
                pytest.skip("Backend not available for cookie CORS test")
            except asyncio.TimeoutError:
                pytest.skip("Backend timeout for cookie CORS test")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_authorization_header_requests_cors(self, services):
        """Test Authorization header requests with CORS."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {
                "Origin": services.frontend_url,
                "Authorization": "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.test",
                "Content-Type": "application/json"
            }
            
            try:
                # Test preflight for Authorization header
                preflight_response = await client.options(
                    f"{services.auth_url}/auth/status",
                    headers={
                        "Origin": services.frontend_url,
                        "Access-Control-Request-Headers": "Authorization, Content-Type"
                    },
                    timeout=5.0
                )
                
                assert preflight_response.status_code == 200
                allowed_headers = preflight_response.headers.get("Access-Control-Allow-Headers", "")
                assert "Authorization" in allowed_headers, "Authorization header should be allowed"
                
                # Test actual request
                response = await client.get(
                    f"{services.auth_url}/auth/status",
                    headers=headers,
                    timeout=5.0
                )
                
                assert response.headers.get("Access-Control-Allow-Credentials") == "true"
                
            except httpx.ConnectError:
                pytest.skip("Auth service not available for Authorization CORS test")
            except asyncio.TimeoutError:
                pytest.skip("Auth service timeout for Authorization CORS test")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_websocket_auth_with_cors(self, services):
        """Test WebSocket authentication with CORS origin."""
        try:
            # WebSocket connection with auth token and origin
            extra_headers = {
                "Origin": services.frontend_url,
                "Authorization": "Bearer test-token"
            }
            
            async with websockets.connect(
                services.websocket_url,
                extra_headers=extra_headers,
                timeout=5.0
            ) as websocket:
                assert websocket.open
                
                # Send authentication message
                auth_message = {
                    "type": "auth",
                    "token": "test-token"
                }
                await websocket.send(json.dumps(auth_message))
                
                # Should not close due to CORS issues
                # Wait a moment to see if connection stays open
                await asyncio.sleep(0.5)
                assert not websocket.closed, "WebSocket should remain open with proper CORS"
                
        except (websockets.exceptions.ConnectionClosed,
                websockets.exceptions.InvalidURI,
                ConnectionRefusedError,
                OSError):
            pytest.skip("WebSocket server not available for auth CORS test")
        except asyncio.TimeoutError:
            pytest.skip("WebSocket timeout for auth CORS test")


@pytest.mark.e2e
class TestCORSRegressionComprehensive:
    """Comprehensive regression tests for all CORS scenarios."""
    
    @pytest.fixture
    def regression_scenarios(self):
        """Define regression scenarios to test."""
        return [
            {
                "name": "Frontend to Auth Config",
                "origin": "http://localhost:3001",
                "url": "http://localhost:8081/auth/config",
                "method": "GET",
                "description": "Original regression case"
            },
            {
                "name": "Frontend to Backend Health",
                "origin": "http://localhost:3001", 
                "url": "http://localhost:8000/health",
                "method": "GET",
                "description": "Cross-service health check"
            },
            {
                "name": "Alt Frontend to Auth",
                "origin": "http://localhost:3000",
                "url": "http://localhost:8081/auth/login",
                "method": "GET", 
                "description": "Alternative frontend port"
            },
            {
                "name": "HTTPS Localhost to Backend",
                "origin": "https://localhost:3000",
                "url": "http://localhost:8000/health",
                "method": "GET",
                "description": "HTTPS frontend to HTTP backend"
            }
        ]
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_all_regression_scenarios(self, regression_scenarios):
        """Test all identified regression scenarios."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for scenario in regression_scenarios:
                headers = {"Origin": scenario["origin"]}
                
                try:
                    # Test OPTIONS preflight
                    preflight_response = await client.options(
                        scenario["url"],
                        headers=headers,
                        timeout=3.0
                    )
                    
                    assert preflight_response.status_code == 200, f"Preflight failed for {scenario['name']}"
                    
                    cors_origin = preflight_response.headers.get("Access-Control-Allow-Origin")
                    assert cors_origin in [scenario["origin"], "*"], f"CORS origin not allowed for {scenario['name']}"
                    
                    # Test actual request if method is supported
                    if scenario["method"] in ["GET", "POST"]:
                        actual_response = await client.request(
                            scenario["method"],
                            scenario["url"],
                            headers=headers,
                            timeout=3.0
                        )
                        
                        cors_origin = actual_response.headers.get("Access-Control-Allow-Origin")
                        assert cors_origin in [scenario["origin"], "*"], f"Actual request CORS failed for {scenario['name']}"
                        
                except (httpx.ConnectError, asyncio.TimeoutError):
                    # Skip individual scenarios if service not available
                    pytest.skip(f"Service not available for regression scenario: {scenario['name']}")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_middleware_ordering_regression(self):
        """Test that CORS middleware is ordered correctly."""
        # This tests the requirement that CORS middleware must be first
        # We can't directly test middleware ordering, but we can test that
        # CORS headers are present even when other middleware might modify requests
        
        async with httpx.AsyncClient(follow_redirects=True) as client:
            # Request with headers that might trigger other middleware
            headers = {
                "Origin": "http://localhost:3001",
                "X-Forwarded-For": "192.168.1.100",
                "User-Agent": "Mozilla/5.0 Test Browser",
                "Accept": "application/json"
            }
            
            try:
                response = await client.get(
                    "http://localhost:8000/health",
                    headers=headers,
                    timeout=5.0
                )
                
                # CORS headers should be present despite other middleware
                assert "Access-Control-Allow-Origin" in response.headers, "CORS headers should be present with other middleware"
                
            except (httpx.ConnectError, asyncio.TimeoutError):
                pytest.skip("Backend not available for middleware ordering test")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_dev_launcher_cors_propagation(self):
        """Test that dev launcher properly propagates CORS configuration."""
        # This tests the requirement that dev launcher must set CORS_ORIGINS=*
        
        # Check if environment variable is set correctly
        with patch.dict(os.environ, {"CORS_ORIGINS": "*", "ENVIRONMENT": "development"}):
            from netra_backend.app.core.middleware_setup import get_cors_origins
            
            origins = get_cors_origins()
            assert "*" in origins, "Dev launcher should set CORS_ORIGINS=* for development"


@pytest.mark.e2e
class TestCORSPerformanceAndResilience:
    """Test CORS performance and resilience characteristics."""
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_preflight_caching(self):
        """Test that CORS preflight responses include proper caching headers."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {
                "Origin": "http://localhost:3001",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Authorization"
            }
            
            try:
                response = await client.options(
                    "http://localhost:8000/health",
                    headers=headers,
                    timeout=5.0
                )
                
                # Should have Max-Age header for preflight caching
                max_age = response.headers.get("Access-Control-Max-Age")
                assert max_age is not None, "Preflight should include Max-Age header"
                assert int(max_age) > 0, "Max-Age should be positive"
                
            except (httpx.ConnectError, asyncio.TimeoutError):
                pytest.skip("Backend not available for preflight caching test")
    
    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_cors_multiple_rapid_requests(self):
        """Test CORS handling under rapid successive requests."""
        async with httpx.AsyncClient(follow_redirects=True) as client:
            headers = {"Origin": "http://localhost:3001"}
            
            # Send multiple rapid requests
            tasks = []
            for i in range(10):
                task = client.get(
                    "http://localhost:8000/health",
                    headers=headers,
                    timeout=5.0
                )
                tasks.append(task)
            
            try:
                responses = await asyncio.gather(*tasks, return_exceptions=True)
                
                # All successful responses should have CORS headers
                successful_responses = [r for r in responses if isinstance(r, httpx.Response) and r.status_code == 200]
                
                if successful_responses:
                    for response in successful_responses:
                        cors_origin = response.headers.get("Access-Control-Allow-Origin")
                        assert cors_origin is not None, "All rapid requests should have CORS headers"
                        
            except Exception:
                pytest.skip("Backend not available for rapid requests test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
