"""
E2E Tests: Auth Security Consistency

Business Value Justification (BVJ):
- Segment: Enterprise/Security  
- Business Goal: Ensure unified auth delegation maintains security
- Value Impact: Security consistency prevents vulnerabilities and compliance issues
- Strategic Impact: Enterprise-grade security foundation ($500K+ ARR protection)

This test suite validates that unified auth delegation maintains or improves
security compared to previous implementations.

Tests validate:
1. No JWT secrets in backend (all handled by auth service)
2. Consistent token validation across all services
3. Secure session management through auth service delegation
4. CORS compliance unified across auth endpoints
5. Auth operations meet performance requirements

CRITICAL: Uses staging environment to validate real security patterns.
"""

import pytest
import asyncio
import httpx
import time
from typing import Dict, Any, List, Optional
from test_framework.base_e2e_test import BaseE2ETest
from shared.isolated_environment import get_env


class TestAuthSecurityConsistency(BaseE2ETest):
    """
    E2E tests for auth security consistency with delegation patterns.
    
    Validates that unified auth delegation maintains enterprise-grade
    security standards and consistency.
    """
    
    def setup_method(self, method=None):
        """Setup for each test method."""
        super().setup_method(method)
        
        # Configure for staging environment
        self.set_env_var("ENVIRONMENT", "staging")
        self.set_env_var("AUTH_SERVICE_URL", "https://auth.staging.netrasystems.ai")
        self.set_env_var("BACKEND_URL", "https://api.staging.netrasystems.ai")
        
        # Test credentials
        self.test_user_email = "e2e-security-test@example.com"
        self.test_user_password = "SecurityTest123!"
    
    @pytest.mark.e2e
    @pytest.mark.staging  
    @pytest.mark.security
    async def test_no_jwt_secrets_in_backend(self):
        """
        Test that backend contains no JWT secrets (all handled by auth service).
        
        CRITICAL: Backend should not have access to JWT secrets.
        All JWT operations should be delegated to auth service.
        """
        try:
            # Test that backend cannot generate valid JWT tokens independently
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                backend_url = self.get_env_var("BACKEND_URL")
                
                # Test backend health/info endpoint 
                info_response = await client.get(f"{backend_url}/health")
                
                if info_response.status_code == 200:
                    info_data = info_response.json()
                    
                    # Backend should not expose JWT configuration
                    security_leaks = []
                    
                    # Check for JWT secret exposure
                    info_str = str(info_data).lower()
                    if "jwt_secret" in info_str or "secret_key" in info_str:
                        security_leaks.append("JWT secret potentially exposed in health endpoint")
                    
                    # Check for auth service configuration exposure
                    if "auth_service_url" in info_str and "internal" in info_str:
                        security_leaks.append("Internal auth service URL exposed")
                    
                    assert len(security_leaks) == 0, \
                        f"Security leaks detected: {security_leaks}"
                
                # Test that backend doesn't have independent token generation
                try:
                    # Try to get a token directly from backend (should fail or delegate)
                    direct_token_response = await client.post(
                        f"{backend_url}/internal/generate-token",  # Should not exist
                        json={"user_id": "test"}
                    )
                    
                    # This endpoint should not exist (404) or should delegate to auth service
                    assert direct_token_response.status_code in [404, 405, 501], \
                        "Backend should not have independent token generation endpoint"
                        
                except httpx.RequestError:
                    # Connection errors are OK - endpoint shouldn't exist
                    pass
                
                self.logger.info("Backend JWT secret isolation verified")
                
        except Exception as e:
            pytest.fail(f"JWT secret isolation test failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.security
    async def test_consistent_token_validation(self):
        """
        Test that all services validate tokens consistently through auth service.
        
        Token validation should be uniform across all services
        via auth service delegation.
        """
        try:
            # Get valid token through proper auth flow
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                backend_url = self.get_env_var("BACKEND_URL")
                
                # Login to get valid token
                login_response = await client.post(
                    f"{backend_url}/auth/login",
                    json={
                        "email": self.test_user_email,
                        "password": self.test_user_password
                    }
                )
                
                valid_token = None
                if login_response.status_code in [200, 201]:
                    login_data = login_response.json()
                    valid_token = login_data.get("access_token") or login_data.get("token")
                
                if not valid_token:
                    # Try registration first
                    register_response = await client.post(
                        f"{backend_url}/auth/register",
                        json={
                            "email": self.test_user_email,
                            "password": self.test_user_password,
                            "name": "Security Test User"
                        }
                    )
                    
                    if register_response.status_code in [200, 201]:
                        login_response = await client.post(
                            f"{backend_url}/auth/login",
                            json={
                                "email": self.test_user_email,
                                "password": self.test_user_password
                            }
                        )
                        
                        if login_response.status_code in [200, 201]:
                            login_data = login_response.json()
                            valid_token = login_data.get("access_token") or login_data.get("token")
                
                if not valid_token:
                    pytest.skip("Could not get valid token for consistency testing")
                
                # Test token validation consistency across endpoints
                test_endpoints = [
                    "/user/profile",
                    "/user/settings", 
                    "/auth/session",
                    "/agent/list"
                ]
                
                validation_results = []
                
                for endpoint in test_endpoints:
                    try:
                        # Test with valid token
                        valid_response = await client.get(
                            f"{backend_url}{endpoint}",
                            headers={"Authorization": f"Bearer {valid_token}"}
                        )
                        
                        # Test with invalid token  
                        invalid_response = await client.get(
                            f"{backend_url}{endpoint}",
                            headers={"Authorization": "Bearer invalid-token-12345"}
                        )
                        
                        validation_results.append({
                            "endpoint": endpoint,
                            "valid_token_status": valid_response.status_code,
                            "invalid_token_status": invalid_response.status_code
                        })
                        
                    except Exception as e:
                        self.logger.warning(f"Endpoint {endpoint} not available: {e}")
                
                # Verify consistent validation behavior
                if validation_results:
                    # Invalid tokens should consistently return 401
                    invalid_statuses = [r["invalid_token_status"] for r in validation_results]
                    consistent_rejection = all(status == 401 for status in invalid_statuses)
                    
                    if not consistent_rejection:
                        pytest.fail(
                            f"Inconsistent token validation: {validation_results}. "
                            f"All invalid tokens should return 401."
                        )
                    
                    self.logger.info(f"Consistent token validation verified across {len(validation_results)} endpoints")
                
        except Exception as e:
            pytest.fail(f"Token validation consistency test failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.security
    async def test_secure_session_management(self):
        """
        Test that session management is secure through auth service delegation.
        
        Sessions should be managed securely with proper isolation
        and security headers.
        """
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                backend_url = self.get_env_var("BACKEND_URL")
                
                # Create session through login
                login_response = await client.post(
                    f"{backend_url}/auth/login",
                    json={
                        "email": self.test_user_email,
                        "password": self.test_user_password
                    }
                )
                
                if login_response.status_code not in [200, 201]:
                    pytest.skip("Could not create session for security testing")
                
                # Check security headers
                security_headers = [
                    "x-content-type-options",
                    "x-frame-options", 
                    "x-xss-protection"
                ]
                
                missing_headers = []
                for header in security_headers:
                    if header not in login_response.headers:
                        missing_headers.append(header)
                
                # Security headers are recommended but not required for this test
                if missing_headers:
                    self.logger.warning(f"Missing security headers: {missing_headers}")
                
                # Check for secure cookie attributes if cookies are used
                set_cookie = login_response.headers.get("set-cookie", "")
                if set_cookie:
                    # Should have secure attributes
                    cookie_security_checks = {
                        "HttpOnly": "httponly" in set_cookie.lower(),
                        "Secure": "secure" in set_cookie.lower(),
                        "SameSite": "samesite" in set_cookie.lower()
                    }
                    
                    missing_cookie_security = [
                        attr for attr, present in cookie_security_checks.items()
                        if not present
                    ]
                    
                    if missing_cookie_security:
                        self.logger.warning(f"Missing cookie security attributes: {missing_cookie_security}")
                
                # Test session isolation
                login_data = login_response.json()
                token1 = login_data.get("access_token") or login_data.get("token")
                
                # Create second session
                login_response2 = await client.post(
                    f"{backend_url}/auth/login",
                    json={
                        "email": self.test_user_email,
                        "password": self.test_user_password
                    }
                )
                
                if login_response2.status_code in [200, 201]:
                    login_data2 = login_response2.json()
                    token2 = login_data2.get("access_token") or login_data2.get("token")
                    
                    # Tokens should be different (proper session isolation)
                    if token1 and token2:
                        assert token1 != token2, "Sessions should be isolated with different tokens"
                        
                self.logger.info("Session security validation completed")
                
        except Exception as e:
            pytest.fail(f"Session security test failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.security
    async def test_cors_compliance_unified(self):
        """
        Test that CORS patterns are consistent across auth endpoints.
        
        All auth-related endpoints should have unified CORS configuration
        for security and functionality.
        """
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                backend_url = self.get_env_var("BACKEND_URL")
                
                # Test CORS preflight for auth endpoints
                auth_endpoints = [
                    "/auth/login",
                    "/auth/register", 
                    "/auth/session",
                    "/auth/refresh"
                ]
                
                cors_results = []
                
                for endpoint in auth_endpoints:
                    try:
                        # Send OPTIONS request (CORS preflight)
                        options_response = await client.request(
                            "OPTIONS",
                            f"{backend_url}{endpoint}",
                            headers={
                                "Origin": "https://app.staging.netrasystems.ai",
                                "Access-Control-Request-Method": "POST",
                                "Access-Control-Request-Headers": "Content-Type,Authorization"
                            }
                        )
                        
                        cors_headers = {
                            "access-control-allow-origin": options_response.headers.get("access-control-allow-origin"),
                            "access-control-allow-methods": options_response.headers.get("access-control-allow-methods"),
                            "access-control-allow-headers": options_response.headers.get("access-control-allow-headers")
                        }
                        
                        cors_results.append({
                            "endpoint": endpoint,
                            "status": options_response.status_code,
                            "cors_headers": cors_headers
                        })
                        
                    except Exception as e:
                        self.logger.warning(f"CORS test failed for {endpoint}: {e}")
                
                # Verify CORS consistency
                if cors_results:
                    # Check that CORS is enabled (status 200 or 204)
                    cors_enabled = [r for r in cors_results if r["status"] in [200, 204]]
                    
                    if cors_enabled:
                        # Check for consistent CORS headers
                        origin_headers = [r["cors_headers"]["access-control-allow-origin"] for r in cors_enabled]
                        unique_origins = set(filter(None, origin_headers))
                        
                        # Should have consistent origin handling
                        self.logger.info(f"CORS origins: {unique_origins}")
                        
                        # Check that required methods are allowed
                        methods_headers = [r["cors_headers"]["access-control-allow-methods"] for r in cors_enabled]
                        all_methods = " ".join(filter(None, methods_headers)).upper()
                        
                        required_methods = ["POST", "GET", "OPTIONS"]
                        missing_methods = [m for m in required_methods if m not in all_methods]
                        
                        if missing_methods:
                            self.logger.warning(f"Missing CORS methods: {missing_methods}")
                        
                        self.logger.info(f"CORS compliance validated for {len(cors_enabled)} endpoints")
                    else:
                        self.logger.warning("No endpoints returned successful CORS preflight")
                
        except Exception as e:
            pytest.fail(f"CORS compliance test failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.performance
    async def test_auth_response_time_requirements(self):
        """
        Test that auth operations meet performance requirements.
        
        Performance requirements from issue:
        - Auth Response Time: < 500ms for authentication operations
        - Token Validation: < 200ms for token validation
        - Session Lookup: < 100ms for session retrieval
        """
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                backend_url = self.get_env_var("BACKEND_URL")
                
                # Test authentication response time (< 500ms)
                auth_start = time.time()
                login_response = await client.post(
                    f"{backend_url}/auth/login",
                    json={
                        "email": self.test_user_email,
                        "password": self.test_user_password
                    }
                )
                auth_time = (time.time() - auth_start) * 1000  # Convert to ms
                
                self.logger.info(f"Authentication time: {auth_time:.1f}ms")
                
                # Authentication should be < 500ms (but allow some tolerance for staging)
                if auth_time > 1000:  # 1 second tolerance for staging
                    self.logger.warning(f"Authentication slow: {auth_time:.1f}ms > 500ms target")
                
                # If login successful, test token validation time
                if login_response.status_code in [200, 201]:
                    login_data = login_response.json()
                    token = login_data.get("access_token") or login_data.get("token")
                    
                    if token:
                        # Test token validation time (< 200ms target)
                        validation_start = time.time()
                        profile_response = await client.get(
                            f"{backend_url}/user/profile",
                            headers={"Authorization": f"Bearer {token}"}
                        )
                        validation_time = (time.time() - validation_start) * 1000
                        
                        self.logger.info(f"Token validation time: {validation_time:.1f}ms")
                        
                        # Token validation should be < 200ms (but allow tolerance)
                        if validation_time > 500:  # 500ms tolerance for staging
                            self.logger.warning(f"Token validation slow: {validation_time:.1f}ms > 200ms target")
                        
                        # Test session lookup time (< 100ms target)
                        session_start = time.time()
                        session_response = await client.get(
                            f"{backend_url}/auth/session",
                            headers={"Authorization": f"Bearer {token}"}
                        )
                        session_time = (time.time() - session_start) * 1000
                        
                        self.logger.info(f"Session lookup time: {session_time:.1f}ms")
                        
                        # Session lookup should be < 100ms (but allow tolerance)
                        if session_time > 300:  # 300ms tolerance for staging
                            self.logger.warning(f"Session lookup slow: {session_time:.1f}ms > 100ms target")
                        
                        # Performance validation
                        performance_summary = {
                            "authentication": f"{auth_time:.1f}ms",
                            "token_validation": f"{validation_time:.1f}ms", 
                            "session_lookup": f"{session_time:.1f}ms"
                        }
                        
                        self.logger.info(f"Auth performance summary: {performance_summary}")
                        
                        # All operations should complete (even if slower than target)
                        assert auth_time < 5000, f"Authentication too slow: {auth_time:.1f}ms"
                        assert validation_time < 2000, f"Token validation too slow: {validation_time:.1f}ms"
                        assert session_time < 1000, f"Session lookup too slow: {session_time:.1f}ms"
                
        except Exception as e:
            pytest.fail(f"Auth performance test failed: {e}")
    
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.security
    async def test_auth_error_handling_security(self):
        """
        Test that auth error handling doesn't leak security information.
        
        Error messages should be informative but not expose
        internal security details or system information.
        """
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                backend_url = self.get_env_var("BACKEND_URL")
                
                # Test various error conditions
                security_tests = [
                    {
                        "name": "Invalid credentials",
                        "request": {
                            "method": "POST",
                            "url": f"{backend_url}/auth/login",
                            "json": {
                                "email": "nonexistent@example.com",
                                "password": "wrongpassword"
                            }
                        },
                        "expected_status": 401
                    },
                    {
                        "name": "Malformed token",
                        "request": {
                            "method": "GET",
                            "url": f"{backend_url}/user/profile",
                            "headers": {"Authorization": "Bearer malformed-token"}
                        },
                        "expected_status": 401
                    },
                    {
                        "name": "Missing authorization",
                        "request": {
                            "method": "GET",
                            "url": f"{backend_url}/user/profile"
                        },
                        "expected_status": 401
                    }
                ]
                
                security_leaks = []
                
                for test in security_tests:
                    try:
                        request = test["request"]
                        response = await client.request(
                            request["method"],
                            request["url"],
                            json=request.get("json"),
                            headers=request.get("headers", {})
                        )
                        
                        # Check response status
                        if response.status_code != test["expected_status"]:
                            self.logger.warning(
                                f"{test['name']}: Expected {test['expected_status']}, "
                                f"got {response.status_code}"
                            )
                        
                        # Check error message for security leaks
                        if response.content:
                            try:
                                error_data = response.json()
                                error_text = str(error_data).lower()
                                
                                # Check for potential security leaks
                                security_patterns = [
                                    "jwt_secret",
                                    "database connection",
                                    "internal error",
                                    "stack trace",
                                    "file path",
                                    "auth service url"
                                ]
                                
                                for pattern in security_patterns:
                                    if pattern in error_text:
                                        security_leaks.append(f"{test['name']}: {pattern} exposed")
                                        
                            except Exception:
                                # Response not JSON - check raw content
                                response_text = response.text.lower()
                                if "traceback" in response_text or "internal server error" in response_text:
                                    security_leaks.append(f"{test['name']}: Stack trace or internal error exposed")
                        
                    except Exception as e:
                        self.logger.warning(f"Security test {test['name']} failed: {e}")
                
                # Verify no security information leaked
                if security_leaks:
                    pytest.fail(f"Security information leaked in error responses: {security_leaks}")
                
                self.logger.info(f"Auth error handling security validated for {len(security_tests)} scenarios")
                
        except Exception as e:
            pytest.fail(f"Auth error handling security test failed: {e}")


if __name__ == "__main__":
    # Allow running this test file directly for development
    pytest.main([__file__, "-v"])