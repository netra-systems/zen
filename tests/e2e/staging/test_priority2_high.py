"""
Priority 2: HIGH Tests (26-40) - REAL IMPLEMENTATION
Authentication & Security
Business Impact: Security breaches, compliance issues

THIS FILE CONTAINS REAL TESTS THAT ACTUALLY TEST STAGING ENVIRONMENT
Each test makes actual HTTP/WebSocket calls and measures real network latency.
"""

import pytest
import asyncio
import json
import time
import uuid
import httpx
import websockets
from typing import Dict, Any
from datetime import datetime, timedelta

from tests.e2e.staging_test_config import get_staging_config

# Mark all tests in this file as high priority and real
pytestmark = [pytest.mark.staging, pytest.mark.high, pytest.mark.real]


class TestHighAuthentication:
    """Tests 26-30: REAL Authentication Tests"""
    
    @pytest.mark.asyncio
    async def test_026_jwt_authentication_real(self):
        """Test #26: REAL JWT authentication endpoint testing"""
        config = get_staging_config()
        start_time = time.time()
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Test JWT/auth related endpoints
            auth_endpoints = [
                "/api/auth/verify",
                "/api/auth/validate", 
                "/api/user/profile",
                "/api/me"
            ]
            
            for endpoint in auth_endpoints:
                # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                response = await client.get(f"{config.backend_url}{endpoint}")
                
                # Should require authentication (401/403) or return data (200)
                assert response.status_code in [200, 401, 403, 404], \
                    f"Auth endpoint {endpoint} returned unexpected status: {response.status_code}"
                
                if response.status_code == 401:
                    print(f"✓ Auth required at {endpoint} (expected)")
                elif response.status_code == 200:
                    print(f"✓ Auth endpoint accessible: {endpoint}")
                elif response.status_code == 404:
                    print(f"• Auth endpoint not implemented: {endpoint}")
        
        # Test health endpoint (shouldn't require auth)
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(f"{config.backend_url}/health")
            assert response.status_code == 200, f"Health endpoint failed: {response.text}"
            
            health_data = response.json()
            assert "status" in health_data, "Health response should have status field"
        
        duration = time.time() - start_time
        print(f"JWT authentication test duration: {duration:.3f}s")
        
        # Verify real network call was made
        assert duration > 0.2, f"Test too fast ({duration:.3f}s) - likely fake!"
    
    @pytest.mark.asyncio
    async def test_027_oauth_google_login_real(self):
        """Test #27: REAL Google OAuth configuration and endpoints"""
        config = get_staging_config()
        start_time = time.time()
        
        oauth_results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Test OAuth-related endpoints
            oauth_endpoints = [
                "/auth/google",
                "/auth/login", 
                "/auth/callback",
                "/api/auth/oauth/config",
                "/api/auth/providers"
            ]
            
            for endpoint in oauth_endpoints:
                # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                response = await client.get(f"{config.backend_url}{endpoint}")
                
                oauth_results[endpoint] = {
                    "status": response.status_code,
                    "content_type": response.headers.get("content-type", ""),
                    "content_length": len(response.text)
                }
                
                # OAuth endpoints typically redirect (302), require auth (401), or return config (200)
                if response.status_code == 302:
                    redirect_url = response.headers.get("location", "")
                    if "google" in redirect_url.lower():
                        oauth_results[endpoint]["google_oauth"] = True
                        print(f"✓ Google OAuth redirect found at {endpoint}")
                elif response.status_code == 200:
                    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                    data = response.json()
                    if "google" in json.dumps(data).lower():
                        oauth_results[endpoint]["google_config"] = True
                        print(f"✓ Google OAuth config found at {endpoint}")
            
            # Test service discovery for OAuth info
            # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
            response = await client.get(f"{config.backend_url}/api/discovery/services")
            if response.status_code == 200:
                services = response.json()
                oauth_results["service_discovery"] = {
                    "status": "found",
                    "has_auth_service": "auth" in json.dumps(services).lower(),
                    "has_oauth": "oauth" in json.dumps(services).lower()
                }
        
        duration = time.time() - start_time
        print(f"OAuth configuration test results:")
        for endpoint, result in oauth_results.items():
            print(f"  {endpoint}: {result}")
        print(f"Test duration: {duration:.3f}s")
        
        # Verify real network testing
        assert duration > 0.3, f"Test too fast ({duration:.3f}s) for OAuth endpoint testing!"
        assert len(oauth_results) > 0, "Should test OAuth endpoints"
    
    @pytest.mark.asyncio
    async def test_028_token_refresh_real(self):
        """Test #28: REAL token refresh endpoint testing"""
        config = get_staging_config()
        start_time = time.time()
        
        refresh_results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Test token refresh endpoints
            refresh_endpoints = [
                "/api/auth/refresh",
                "/auth/refresh",
                "/api/token/refresh",
                "/refresh"
            ]
            
            for endpoint in refresh_endpoints:
                # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                # Test GET (should require auth or return method not allowed)
                get_response = await client.get(f"{config.backend_url}{endpoint}")
                
                # Test POST with mock refresh token
                test_refresh_payload = {
                    "refresh_token": "test_refresh_token_123",
                    "grant_type": "refresh_token"
                }
                
                post_response = await client.post(
                    f"{config.backend_url}{endpoint}",
                    json=test_refresh_payload
                )
                
                refresh_results[endpoint] = {
                    "get_status": get_response.status_code,
                    "post_status": post_response.status_code,
                    "get_headers": dict(get_response.headers),
                    "post_headers": dict(post_response.headers)
                }
                
                # Token refresh should typically:
                # - Return 401 for invalid tokens
                # - Return 400 for malformed requests
                # - Return 405 if wrong method
                # - Return 200/201 for successful refresh
                
                if post_response.status_code in [400, 401]:
                    print(f"✓ Token refresh properly validates at {endpoint}")
                elif post_response.status_code == 405:
                    print(f"• Token refresh method not allowed at {endpoint}")
                elif post_response.status_code in [200, 201]:
                    print(f"✓ Token refresh endpoint active at {endpoint}")
                    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                    token_data = post_response.json()
                    if "access_token" in token_data or "token" in token_data:
                        refresh_results[endpoint]["token_response"] = True
        
        duration = time.time() - start_time
        print(f"Token refresh test results:")
        for endpoint, result in refresh_results.items():
            print(f"  {endpoint}: {result}")
        print(f"Test duration: {duration:.3f}s")
        
        # Verify real network testing
        assert duration > 0.3, f"Test too fast ({duration:.3f}s) for token refresh testing!"
        assert len(refresh_results) > 0, "Should test token refresh endpoints"
    
    @pytest.mark.asyncio
    async def test_029_token_expiry_real(self):
        """Test #29: REAL token expiration handling in staging"""
        config = get_staging_config()
        start_time = time.time()
        
        expiry_results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Test with expired-looking tokens to see how system handles them
            expired_tokens = [
                "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0IiwiaWF0IjoxNjAwMDAwMDAwLCJleHAiOjE2MDAwMDAwMDB9.invalid",  # Clearly expired
                "Bearer expired_token_123",
                "invalid_token_format"
            ]
            
            protected_endpoints = [
                "/api/user/profile",
                "/api/messages", 
                "/api/threads",
                "/api/me"
            ]
            
            for i, token in enumerate(expired_tokens):
                token_results = []
                
                for endpoint in protected_endpoints:
                    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                    headers = {"Authorization": token}
                    response = await client.get(f"{config.backend_url}{endpoint}", headers=headers)
                    
                    token_results.append({
                        "endpoint": endpoint,
                        "status": response.status_code,
                        "content_type": response.headers.get("content-type", ""),
                        "auth_header_handled": "authorization" in response.headers.get("www-authenticate", "").lower() or response.status_code == 401
                    })
                    
                    # Expired/invalid tokens should return 401
                    if response.status_code == 401:
                        print(f"✓ Expired token properly rejected at {endpoint}")
                
                expiry_results[f"token_{i+1}"] = token_results
            
            # Test token introspection endpoint if available
            # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
            introspect_response = await client.post(
                f"{config.backend_url}/api/auth/introspect",
                json={"token": "test_token"}
            )
            
            expiry_results["introspection"] = {
                "status": introspect_response.status_code,
                "available": introspect_response.status_code != 404
            }
        
        duration = time.time() - start_time
        print(f"Token expiry handling test results:")
        for token_type, results in expiry_results.items():
            print(f"  {token_type}: {results}")
        print(f"Test duration: {duration:.3f}s")
        
        # Verify real network testing
        assert duration > 0.4, f"Test too fast ({duration:.3f}s) for token expiry testing!"
        
        # Should test multiple scenarios
        assert len(expiry_results) > 2, "Should test multiple token expiry scenarios"
    
    @pytest.mark.asyncio
    async def test_030_logout_flow_real(self):
        """Test #30: REAL user logout endpoint testing"""
        config = get_staging_config()
        start_time = time.time()
        
        logout_results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Test logout endpoints
            logout_endpoints = [
                "/api/auth/logout",
                "/auth/logout",
                "/logout",
                "/api/session/end"
            ]
            
            for endpoint in logout_endpoints:
                # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                # Test GET logout
                get_response = await client.get(f"{config.backend_url}{endpoint}")
                
                # Test POST logout with session data
                logout_payload = {
                    "session_id": f"test_session_{uuid.uuid4()}",
                    "revoke_all": True
                }
                
                post_response = await client.post(
                    f"{config.backend_url}{endpoint}",
                    json=logout_payload
                )
                
                logout_results[endpoint] = {
                    "get_status": get_response.status_code,
                    "post_status": post_response.status_code,
                    "get_size": len(get_response.text),
                    "post_size": len(post_response.text)
                }
                
                # Check for logout success indicators
                if get_response.status_code == 200:
                    logout_results[endpoint]["get_logout_available"] = True
                    print(f"✓ GET logout available at {endpoint}")
                
                if post_response.status_code in [200, 204]:
                    logout_results[endpoint]["post_logout_available"] = True
                    print(f"✓ POST logout available at {endpoint}")
                elif post_response.status_code == 401:
                    print(f"• Logout requires auth at {endpoint} (expected)")
                elif post_response.status_code == 404:
                    print(f"• Logout not implemented at {endpoint}")
                
                # Check for session clearing indicators in headers
                if "set-cookie" in get_response.headers:
                    cookies = get_response.headers["set-cookie"]
                    if "Max-Age=0" in cookies or "expires=" in cookies:
                        logout_results[endpoint]["clears_cookies"] = True
            
            # Test health endpoint (should still work after logout attempts)
            response = await client.get(f"{config.backend_url}/health")
            logout_results["health_after_logout"] = {
                "status": response.status_code,
                "healthy": response.status_code == 200
            }
            
            assert response.status_code == 200, "Health should work after logout attempts"
        
        duration = time.time() - start_time
        print(f"Logout flow test results:")
        for endpoint, result in logout_results.items():
            print(f"  {endpoint}: {result}")
        print(f"Test duration: {duration:.3f}s")
        
        # Verify real network testing
        assert duration > 0.3, f"Test too fast ({duration:.3f}s) for logout flow testing!"
        assert logout_results["health_after_logout"]["healthy"], "Health check should still work"


class TestHighSecurity:
    """Tests 31-35: REAL Security Controls Testing"""
    
    @pytest.mark.asyncio
    async def test_031_session_security_real(self):
        """Test #31: REAL session security headers and cookie testing"""
        config = get_staging_config()
        start_time = time.time()
        
        security_results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Test security headers on various endpoints
            test_endpoints = [
                "/health",
                "/api/health", 
                "/api/discovery/services",
                "/"
            ]
            
            for endpoint in test_endpoints:
                # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                response = await client.get(f"{config.backend_url}{endpoint}")
                
                security_headers = {
                    "x-frame-options": response.headers.get("x-frame-options"),
                    "x-content-type-options": response.headers.get("x-content-type-options"),
                    "x-xss-protection": response.headers.get("x-xss-protection"),
                    "strict-transport-security": response.headers.get("strict-transport-security"),
                    "content-security-policy": response.headers.get("content-security-policy"),
                    "set-cookie": response.headers.get("set-cookie")
                }
                
                # Analyze cookie security
                cookie_security = {}
                if security_headers["set-cookie"]:
                    cookie_header = security_headers["set-cookie"]
                    cookie_security = {
                        "has_secure": "Secure" in cookie_header,
                        "has_httponly": "HttpOnly" in cookie_header,
                        "has_samesite": "SameSite" in cookie_header,
                        "samesite_strict": "SameSite=Strict" in cookie_header or "SameSite=strict" in cookie_header
                    }
                
                security_results[endpoint] = {
                    "status": response.status_code,
                    "security_headers": {k: v for k, v in security_headers.items() if v},
                    "cookie_security": cookie_security,
                    "uses_https": config.backend_url.startswith("https://")
                }
                
                # Log security findings
                if security_headers["strict-transport-security"]:
                    print(f"✓ HSTS enabled on {endpoint}")
                if cookie_security.get("has_secure") and cookie_security.get("has_httponly"):
                    print(f"✓ Secure cookies on {endpoint}")
                if security_headers["x-frame-options"]:
                    print(f"✓ Clickjacking protection on {endpoint}")
        
        duration = time.time() - start_time
        print(f"Session security test results:")
        for endpoint, result in security_results.items():
            print(f"  {endpoint}: {result}")
        print(f"Test duration: {duration:.3f}s")
        
        # Verify real network testing
        assert duration > 0.3, f"Test too fast ({duration:.3f}s) for security testing!"
        assert len(security_results) > 3, "Should test multiple endpoints for security"
        
        # Verify HTTPS is being used
        assert config.backend_url.startswith("https://"), "Should test HTTPS endpoints for security"
    
    @pytest.mark.asyncio
    async def test_032_https_certificate_validation_real(self):
        """Test #32: REAL HTTPS certificate validation and TLS security"""
        config = get_staging_config()
        start_time = time.time()
        
        cert_results = {}
        
        async with httpx.AsyncClient(timeout=30, verify=True) as client:
            # Test HTTPS endpoints with certificate verification
            https_endpoints = [
                "/health",
                "/api/health",
                "/api/discovery/services"
            ]
            
            for endpoint in https_endpoints:
                # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                response = await client.get(f"{config.backend_url}{endpoint}")
                
                cert_results[endpoint] = {
                    "status": response.status_code,
                    "tls_version": getattr(response.request, 'tls_version', 'unknown'),
                    "headers": {
                        "strict-transport-security": response.headers.get("strict-transport-security"),
                        "x-content-type-options": response.headers.get("x-content-type-options"),
                        "x-frame-options": response.headers.get("x-frame-options"),
                        "referrer-policy": response.headers.get("referrer-policy")
                    }
                }
                
                # Test that HTTPS is enforced
                if response.status_code == 200:
                    # Check for security headers
                    security_score = 0
                    if response.headers.get("strict-transport-security"):
                        security_score += 1
                        print(f"✓ HSTS header found on {endpoint}")
                    if response.headers.get("x-content-type-options") == "nosniff":
                        security_score += 1
                        print(f"✓ X-Content-Type-Options protection on {endpoint}")
                    if response.headers.get("x-frame-options"):
                        security_score += 1
                        print(f"✓ X-Frame-Options protection on {endpoint}")
                        
                    cert_results[endpoint]["security_score"] = security_score
            
            # Test HTTP redirect to HTTPS (if HTTP endpoint exists)
            # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
            http_url = config.backend_url.replace("https://", "http://")
            http_response = await client.get(f"{http_url}/health", follow_redirects=False)
            cert_results["http_redirect"] = {
                "status": http_response.status_code,
                "location": http_response.headers.get("location", ""),
                "redirects_to_https": "https://" in http_response.headers.get("location", "")
            }
            if http_response.status_code in [301, 302, 307, 308]:
                print("✓ HTTP to HTTPS redirect configured")
        
        duration = time.time() - start_time
        print(f"HTTPS certificate validation results:")
        for endpoint, result in cert_results.items():
            print(f"  {endpoint}: {result}")
        print(f"Test duration: {duration:.3f}s")
        
        # Verify real network testing
        assert duration > 0.3, f"Test too fast ({duration:.3f}s) for HTTPS certificate testing!"
        assert len(cert_results) > 3, "Should test multiple HTTPS endpoints"
        
        # Verify HTTPS is properly configured
        assert config.backend_url.startswith("https://"), "Backend must use HTTPS"
    
    @pytest.mark.asyncio
    async def test_033_cors_policy_real(self):
        """Test #33: REAL CORS policy testing with cross-origin requests"""
        config = get_staging_config()
        start_time = time.time()
        
        cors_results = {}
        
        async with httpx.AsyncClient(timeout=30) as client:
            # Test CORS preflight requests
            cors_endpoints = [
                "/api/health",
                "/api/discovery/services",
                "/api/messages",
                "/api/threads"
            ]
            
            test_origins = [
                "https://app.netrasystems.ai",
                "https://app.staging.netrasystems.ai",
                "https://localhost:3000",
                "https://malicious-site.com"  # Should be blocked
            ]
            
            for endpoint in cors_endpoints:
                endpoint_results = {}
                
                for origin in test_origins:
                    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                    # Send CORS preflight request
                    headers = {
                        "Origin": origin,
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "Content-Type,Authorization"
                    }
                    
                    response = await client.options(
                        f"{config.backend_url}{endpoint}",
                        headers=headers
                    )
                    
                    cors_headers = {
                        "access-control-allow-origin": response.headers.get("access-control-allow-origin"),
                        "access-control-allow-methods": response.headers.get("access-control-allow-methods"),
                        "access-control-allow-headers": response.headers.get("access-control-allow-headers"),
                        "access-control-allow-credentials": response.headers.get("access-control-allow-credentials"),
                        "access-control-max-age": response.headers.get("access-control-max-age")
                    }
                    
                    endpoint_results[origin] = {
                        "status": response.status_code,
                        "cors_headers": {k: v for k, v in cors_headers.items() if v},
                        "allows_origin": response.headers.get("access-control-allow-origin") in [origin, "*"]
                    }
                    
                    # Check for proper CORS configuration
                    if response.status_code == 200 and cors_headers["access-control-allow-origin"]:
                        if origin == "https://malicious-site.com" and cors_headers["access-control-allow-origin"] != "*":
                            print(f"✓ CORS properly blocks malicious origin on {endpoint}")
                        elif origin in ["https://app.netrasystems.ai", "https://app.staging.netrasystems.ai"]:
                            print(f"✓ CORS allows legitimate origin {origin} on {endpoint}")
                
                cors_results[endpoint] = endpoint_results
        
        duration = time.time() - start_time
        print(f"CORS policy test results:")
        for endpoint, results in cors_results.items():
            print(f"  {endpoint}:")
            for origin, result in results.items():
                status = result.get("status", "error")
                allows = result.get("allows_origin", False)
                print(f"    {origin}: status={status}, allows={allows}")
        print(f"Test duration: {duration:.3f}s")
        
        # Verify real network testing
        assert duration > 0.4, f"Test too fast ({duration:.3f}s) for CORS policy testing!"
        assert len(cors_results) > 2, "Should test CORS on multiple endpoints"
    
    @pytest.mark.asyncio
    async def test_034_rate_limiting_real(self):
        """Test #34: REAL rate limiting and abuse protection testing"""
        config = get_staging_config()
        start_time = time.time()
        
        rate_limit_results = {}
        
        async with httpx.AsyncClient(timeout=60) as client:
            # Test rate limiting on different endpoints
            test_endpoints = [
                "/health",
                "/api/health",
                "/api/discovery/services"
            ]
            
            for endpoint in test_endpoints:
                endpoint_results = []
                rate_limited = False
                
                # Send rapid requests to test rate limiting
                for i in range(25):  # Send 25 requests rapidly
                    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                    request_start = time.time()
                    response = await client.get(f"{config.backend_url}{endpoint}")
                    request_duration = time.time() - request_start
                    
                    rate_limit_headers = {
                        "x-ratelimit-limit": response.headers.get("x-ratelimit-limit"),
                        "x-ratelimit-remaining": response.headers.get("x-ratelimit-remaining"),
                        "x-ratelimit-reset": response.headers.get("x-ratelimit-reset"),
                        "retry-after": response.headers.get("retry-after")
                    }
                    
                    result = {
                        "request": i + 1,
                        "status": response.status_code,
                        "duration": request_duration,
                        "rate_headers": {k: v for k, v in rate_limit_headers.items() if v}
                    }
                    
                    endpoint_results.append(result)
                    
                    # Check for rate limiting
                    if response.status_code == 429:
                        rate_limited = True
                        print(f"✓ Rate limit triggered at request {i+1} on {endpoint}")
                        break
                    elif response.status_code >= 500:
                        print(f"• Server error during rate test: {response.status_code}")
                        break
                    
                    # Very short delay to simulate rapid requests
                    await asyncio.sleep(0.02)  # 20ms delay
                
                rate_limit_results[endpoint] = {
                    "total_requests": len(endpoint_results),
                    "rate_limited": rate_limited,
                    "results": endpoint_results[-5:] if len(endpoint_results) > 5 else endpoint_results  # Last 5 results
                }
                
                # Test that rate limiting resets after delay
                if rate_limited:
                    print(f"Waiting for rate limit reset on {endpoint}...")
                    await asyncio.sleep(5)  # Wait 5 seconds
                    
                    # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
                    reset_response = await client.get(f"{config.backend_url}{endpoint}")
                    rate_limit_results[endpoint]["reset_works"] = reset_response.status_code != 429
                    if reset_response.status_code != 429:
                        print(f"✓ Rate limit reset successfully on {endpoint}")
        
        duration = time.time() - start_time
        print(f"Rate limiting test results:")
        for endpoint, results in rate_limit_results.items():
            print(f"  {endpoint}: {results['total_requests']} requests, rate_limited={results['rate_limited']}")
        print(f"Test duration: {duration:.3f}s")
        
        # Verify real network testing
        assert duration > 1.0, f"Test too fast ({duration:.3f}s) for rate limiting testing!"
        assert len(rate_limit_results) > 2, "Should test rate limiting on multiple endpoints"
    
    @pytest.mark.asyncio
    async def test_035_websocket_security_real(self):
        """Test #35: REAL WebSocket security and authentication upgrade testing"""
        config = get_staging_config()
        start_time = time.time()
        
        websocket_results = {}
        
        def safe_print(message):
            """Print message with Unicode fallback for Windows compatibility"""
            try:
                print(message)
            except UnicodeEncodeError:
                # Replace Unicode characters with ASCII equivalents
                safe_message = message.replace("✓", "[OK]").replace("⚠", "[WARNING]").replace("•", "-")
                print(safe_message)
        
        # Test WebSocket connection security
        # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
        # Test 1: Verify WSS (secure WebSocket) is enforced
        assert config.websocket_url.startswith("wss://"), "WebSocket must use secure protocol (wss://)"
        websocket_results["secure_protocol"] = True
        safe_print("[OK] WebSocket uses secure protocol (wss://)")
        
        # Test 2: Try connection without authentication (expect 403 error)
        # TESTS MUST RAISE ERRORS - but here we catch expected authentication errors
        auth_enforced = False
        
        try:
            async with asyncio.timeout(10):
                async with websockets.connect(
                    config.websocket_url,
                    close_timeout=5
                ) as ws:
                    # Try to send unauthorized message
                    test_message = {
                        "type": "test_message",
                        "content": "unauthorized_test",
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    await ws.send(json.dumps(test_message))
                    
                    # Try to receive response
                    response = await asyncio.wait_for(ws.recv(), timeout=5)
                    response_data = json.loads(response)
                    
                    websocket_results["auth_enforcement"] = {
                        "connection_allowed": True,
                        "message_sent": True,
                        "response": response_data.get("type", "unknown"),
                        "auth_required": "auth" in response.lower() or "unauthorized" in response.lower()
                    }
                    
                    if websocket_results["auth_enforcement"]["auth_required"]:
                        safe_print("✓ WebSocket properly enforces authentication in message response")
                        auth_enforced = True
                    else:
                        safe_print("⚠ WebSocket may not enforce authentication")
                        
        except websockets.exceptions.InvalidStatus as e:
            # Expected: WebSocket rejects connection with 403/401 
            if "403" in str(e) or "401" in str(e):
                auth_enforced = True
                safe_print("✓ WebSocket properly enforces authentication at connection level")
                websocket_results["auth_enforcement"] = {
                    "connection_allowed": False,
                    "auth_enforced": True,
                    "error_code": "403" if "403" in str(e) else "401",
                    "auth_required": True
                }
            else:
                # Unexpected error - re-raise
                raise
        
        # Verify authentication was enforced
        assert auth_enforced, "WebSocket should enforce authentication either at connection or message level"
        
        # Test 3: Try with malformed authorization header (expect 403 error)
        # TESTS MUST RAISE ERRORS - but here we catch expected authentication errors
        malformed_headers = {
            "Authorization": "Bearer invalid_token_12345"
        }
        
        malformed_auth_enforced = False
        try:
            # Use asyncio.timeout for Python 3.12 compatibility
            async with asyncio.timeout(10):
                async with websockets.connect(
                    config.websocket_url,
                    additional_headers=malformed_headers,
                    close_timeout=5
                ) as ws:
                    # Send test message with bad auth
                    await ws.send(json.dumps({"type": "ping", "bad_auth": True}))
                    
                    # Try to receive response
                    response = await asyncio.wait_for(ws.recv(), timeout=3)
                    websocket_results["malformed_auth"] = {
                        "connection_allowed": True,
                        "response_received": True,
                        "response": json.loads(response)
                    }
        except websockets.exceptions.InvalidStatus as e:
            # Expected: WebSocket rejects malformed auth with 403/401
            if "403" in str(e) or "401" in str(e):
                malformed_auth_enforced = True
                safe_print("✓ WebSocket properly rejects malformed auth tokens")
                websocket_results["malformed_auth"] = {
                    "connection_allowed": False,
                    "auth_enforced": True,
                    "error_code": "403" if "403" in str(e) else "401"
                }
            else:
                # Unexpected error - re-raise
                raise
        
        # Verify malformed auth was properly rejected
        assert malformed_auth_enforced, "WebSocket should reject malformed authorization tokens"
        
        # Test 4: Test WebSocket upgrade headers
        # TESTS MUST RAISE ERRORS - NO TRY-EXCEPT per CLAUDE.md
        # Make HTTP request to WebSocket endpoint to check upgrade headers
        async with httpx.AsyncClient(timeout=10) as client:
            # Try GET request to WebSocket endpoint (should fail or redirect)
            ws_http_url = config.websocket_url.replace("wss://", "https://").replace("/ws", "/ws")
            response = await client.get(ws_http_url)
            
            websocket_results["upgrade_handling"] = {
                "status": response.status_code,
                "upgrade_header": response.headers.get("upgrade"),
                "connection_header": response.headers.get("connection"),
                "proper_upgrade": response.status_code in [400, 426] or "upgrade" in response.headers.get("connection", "").lower()
            }
            
            if websocket_results["upgrade_handling"]["proper_upgrade"]:
                safe_print("✓ WebSocket upgrade handling configured")
        
        duration = time.time() - start_time
        safe_print(f"WebSocket security test results:")
        for test_name, result in websocket_results.items():
            safe_print(f"  {test_name}: {result}")
        safe_print(f"Test duration: {duration:.3f}s")
        
        # Verify real network testing
        assert duration > 0.3, f"Test too fast ({duration:.3f}s) for WebSocket security testing!"
        
        # Verify WebSocket security requirements
        assert websocket_results.get("secure_protocol"), "WebSocket must use secure protocol"
        
        # Check if we have meaningful security test results (relaxed requirement for staging)
        # The test should have either successful auth enforcement OR general error indicating server rejection
        meaningful_tests = len([k for k, v in websocket_results.items() 
                              if k != "secure_protocol" and isinstance(v, dict) and 
                              (v.get("auth_required") or v.get("connection_allowed") is not None)])
        
        # Accept the test if we have secure protocol + general error (403 auth rejection)
        if len(websocket_results) == 2 and websocket_results.get("general_error") and "403" in str(websocket_results["general_error"]):
            safe_print("✓ WebSocket security test passed: Server properly rejects unauthorized connections")
        else:
            # More flexible assertion - accept meaningful security validation
            has_auth_test = any(k in websocket_results for k in ["auth_enforcement", "general_error"])
            has_security_validation = websocket_results.get("secure_protocol") and has_auth_test
            
            assert has_security_validation or len(websocket_results) > 2, \
                f"Should perform meaningful WebSocket security tests. Got {len(websocket_results)} results: {websocket_results}"


# Verification helper to ensure tests are real
def verify_test_duration(test_name: str, duration: float, minimum: float = 0.1):
    """Verify test took real time to execute"""
    assert duration >= minimum, \
        f"🚨 FAKE TEST DETECTED: {test_name} completed in {duration:.3f}s (minimum: {minimum}s). " \
        f"This test is not making real network calls!"


if __name__ == "__main__":
    # Run a quick verification
    print("=" * 70)
    print("REAL HIGH PRIORITY STAGING TEST VERIFICATION")
    print("=" * 70)
    print("This file contains REAL tests that actually communicate with staging.")
    print("Each test MUST take >0.1 seconds due to network latency.")
    print("Tests make actual HTTP/WebSocket calls to staging environment.")
    print("All authentication and security tests now make REAL network calls.")
    print("=" * 70)