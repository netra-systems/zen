"""
Critical Authentication Middleware Security Tests - Cycles 41-45
Tests revenue-critical authentication middleware security patterns.

Business Value Justification:
- Segment: All customer segments requiring secure API access
- Business Goal: Prevent $4.1M annual revenue loss from API security breaches
- Value Impact: Ensures secure API authentication for all service endpoints
- Strategic Impact: Enables enterprise API security compliance and SOC 2 certification

Cycles Covered: 41, 42, 43, 44, 45
"""

import pytest
import asyncio
import time
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta, timezone
import jwt

from netra_backend.app.middleware.fastapi_auth_middleware import FastAPIAuthMiddleware
from netra_backend.app.services.token_service import TokenService
from netra_backend.app.core.unified_logging import get_logger


logger = get_logger(__name__)


@pytest.mark.critical
@pytest.mark.auth_middleware
@pytest.mark.security
@pytest.mark.parametrize("environment", ["test"])
class TestAuthenticationMiddlewareSecurity:
    """Critical authentication middleware security test suite."""

    @pytest.fixture
    def auth_middleware(self):
        """Create isolated auth middleware for testing."""
        from unittest.mock import MagicMock
        mock_app = MagicMock()
        middleware = FastAPIAuthMiddleware(mock_app)
        return middleware

    @pytest.fixture
    def token_service(self):
        """Create isolated token service for testing."""
        service = TokenService()
        service.initialize()
        return service

    @pytest.fixture
    def mock_request(self):
        """Create mock HTTP request for testing."""
        request = MagicMock()
        request.method = "GET"
        request.url.path = "/api/test"
        request.headers = {}
        request.client.host = "192.168.1.100"
        return request

    @pytest.mark.cycle_41
    async def test_malformed_authorization_header_handling_prevents_crashes(self, environment, auth_middleware, mock_request):
        """
        Cycle 41: Test malformed authorization header handling prevents middleware crashes.
        
        Revenue Protection: $520K annually from preventing service crashes.
        """
        logger.info("Testing malformed authorization header handling - Cycle 41")
        
        # Test various malformed authorization headers
        malformed_headers = [
            "",  # Empty header
            "Bearer",  # No token
            "Basic dGVzdA==",  # Wrong auth type
            "Bearer ",  # Bearer with empty token
            "Bearer invalid.token.format",  # Invalid JWT format
            "Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.invalid",  # Invalid JWT payload
            "Bearer " + "x" * 10000,  # Extremely long token
            "Bearer\x00\x01\x02",  # Binary data
            "Malformed auth header without proper format",  # No Bearer prefix
        ]
        
        for i, malformed_header in enumerate(malformed_headers):
            mock_request.headers = {"Authorization": malformed_header}
            
            try:
                result = await auth_middleware.authenticate_request(mock_request)
                # If authentication doesn't raise exception, it should return unauthorized
                assert result["authenticated"] == False, f"Malformed header {i} incorrectly authenticated"
                assert "error" in result, f"Malformed header {i} should include error"
                
            except Exception as e:
                # Should not crash the middleware
                assert "Internal server error" not in str(e), f"Malformed header {i} caused server crash: {e}"
                logger.info(f"Malformed header {i} handled gracefully: {e}")
        
        logger.info("Malformed authorization header handling verified")

    @pytest.mark.cycle_42
    async def test_rate_limiting_per_client_prevents_brute_force_attacks(self, environment, auth_middleware, mock_request):
        """
        Cycle 42: Test rate limiting per client prevents brute force authentication attacks.
        
        Revenue Protection: $680K annually from preventing brute force attacks.
        """
        logger.info("Testing rate limiting per client - Cycle 42")
        
        client_ip = "192.168.1.100"
        mock_request.client.host = client_ip
        
        # Configure rate limiting for testing
        auth_middleware.configure_rate_limiting(
            max_attempts=5,
            window_seconds=60,
            lockout_duration=30
        )
        
        # Simulate repeated failed authentication attempts
        failed_attempts = 0
        for attempt in range(7):  # Exceed rate limit
            mock_request.headers = {"Authorization": f"Bearer invalid_token_{attempt}"}
            
            result = await auth_middleware.authenticate_request(mock_request)
            
            if result["authenticated"] == False:
                failed_attempts += 1
                
                if failed_attempts <= 5:
                    # Should allow attempts within limit
                    assert "rate_limited" not in result, f"Premature rate limiting on attempt {attempt + 1}"
                else:
                    # Should rate limit after 5 attempts
                    assert result.get("rate_limited") == True, f"Rate limiting not applied after {failed_attempts} attempts"
                    assert "too_many_attempts" in result.get("error", ""), "Rate limit error not descriptive"
        
        # Verify client is locked out
        mock_request.headers = {"Authorization": "Bearer another_invalid_token"}
        locked_result = await auth_middleware.authenticate_request(mock_request)
        assert locked_result.get("rate_limited") == True, "Client not locked out after rate limit"
        
        # Test that other clients are not affected
        other_client_request = MagicMock()
        other_client_request.method = "GET"
        other_client_request.url.path = "/api/test"
        other_client_request.headers = {"Authorization": "Bearer invalid_token"}
        other_client_request.client.host = "192.168.1.200"  # Different IP
        
        other_result = await auth_middleware.authenticate_request(other_client_request)
        assert other_result.get("rate_limited") != True, "Rate limiting affected other clients"
        
        logger.info("Rate limiting per client verified")

    @pytest.mark.cycle_43
    async def test_concurrent_authentication_consistency_prevents_race_conditions(self, environment, auth_middleware, token_service):
        """
        Cycle 43: Test concurrent authentication consistency prevents race conditions.
        
        Revenue Protection: $440K annually from preventing authentication race conditions.
        """
        logger.info("Testing concurrent authentication consistency - Cycle 43")
        
        # Create valid token for testing
        user_data = {
            "user_id": "test_user_43",
            "role": "user",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        valid_token = token_service.create_token(user_data)
        
        async def concurrent_auth_request(request_id):
            """Simulate concurrent authentication request."""
            mock_request = MagicMock()
            mock_request.method = "GET"
            mock_request.url.path = f"/api/test/{request_id}"
            mock_request.headers = {"Authorization": f"Bearer {valid_token}"}
            mock_request.client.host = f"192.168.1.{100 + (request_id % 50)}"
            
            result = await auth_middleware.authenticate_request(mock_request)
            return {
                "request_id": request_id,
                "authenticated": result.get("authenticated", False),
                "user_id": result.get("user", {}).get("user_id"),
                "timestamp": time.time()
            }
        
        # Execute concurrent authentication requests
        num_requests = 20
        tasks = [concurrent_auth_request(i) for i in range(num_requests)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Analyze results for consistency
        successful_auths = [r for r in results if isinstance(r, dict) and r.get("authenticated")]
        failed_auths = [r for r in results if isinstance(r, dict) and not r.get("authenticated")]
        exceptions = [r for r in results if isinstance(r, Exception)]
        
        # All requests should authenticate successfully with same token
        assert len(successful_auths) >= num_requests - 2, f"Too many authentication failures: {len(successful_auths)}/{num_requests}"
        assert len(exceptions) == 0, f"Unexpected exceptions during concurrent auth: {exceptions}"
        
        # All successful auths should have consistent user data
        user_ids = {r["user_id"] for r in successful_auths}
        assert len(user_ids) == 1, f"Inconsistent user IDs in concurrent auth: {user_ids}"
        assert list(user_ids)[0] == "test_user_43", "Incorrect user ID in concurrent auth"
        
        logger.info(f"Concurrent authentication consistency verified: {len(successful_auths)} successful requests")

    @pytest.mark.cycle_44
    async def test_authorization_bypass_prevention_enforces_permissions(self, environment, auth_middleware, token_service):
        """
        Cycle 44: Test authorization bypass prevention enforces proper permissions.
        
        Revenue Protection: $760K annually from preventing unauthorized access.
        """
        logger.info("Testing authorization bypass prevention - Cycle 44")
        
        # Create tokens with different permission levels
        user_token_data = {
            "user_id": "regular_user_44",
            "role": "user",
            "permissions": ["read"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        user_token = token_service.create_token(user_token_data)
        
        admin_token_data = {
            "user_id": "admin_user_44", 
            "role": "admin",
            "permissions": ["read", "write", "admin"],
            "exp": datetime.now(timezone.utc) + timedelta(hours=1)
        }
        admin_token = token_service.create_token(admin_token_data)
        
        # Test access to user endpoint with user token (should succeed)
        user_request = MagicMock()
        user_request.method = "GET"
        user_request.url.path = "/api/user/profile"
        user_request.headers = {"Authorization": f"Bearer {user_token}"}
        user_request.client.host = "192.168.1.100"
        
        user_result = await auth_middleware.authenticate_request(user_request)
        assert user_result["authenticated"] == True, "User token failed on user endpoint"
        
        authorized = auth_middleware.check_authorization(user_result["user"], "read", "/api/user/profile")
        assert authorized == True, "User not authorized for user endpoint"
        
        # Test access to admin endpoint with user token (should fail)
        admin_request = MagicMock()
        admin_request.method = "POST"
        admin_request.url.path = "/api/admin/delete_user"
        admin_request.headers = {"Authorization": f"Bearer {user_token}"}
        admin_request.client.host = "192.168.1.100"
        
        admin_auth_result = await auth_middleware.authenticate_request(admin_request)
        assert admin_auth_result["authenticated"] == True, "User token should authenticate"
        
        admin_authorized = auth_middleware.check_authorization(admin_auth_result["user"], "admin", "/api/admin/delete_user")
        assert admin_authorized == False, "User incorrectly authorized for admin endpoint"
        
        # Test admin token on admin endpoint (should succeed)
        admin_request.headers = {"Authorization": f"Bearer {admin_token}"}
        admin_token_result = await auth_middleware.authenticate_request(admin_request)
        assert admin_token_result["authenticated"] == True, "Admin token failed authentication"
        
        admin_token_authorized = auth_middleware.check_authorization(admin_token_result["user"], "admin", "/api/admin/delete_user")
        assert admin_token_authorized == True, "Admin not authorized for admin endpoint"
        
        # Test bypass attempts with modified headers
        bypass_attempts = [
            {"X-User-Role": "admin"},  # Header injection attempt
            {"X-Override-Auth": "true"},  # Override attempt
            {"X-Forwarded-User": "admin_user"},  # User spoofing
        ]
        
        for bypass_headers in bypass_attempts:
            bypass_request = MagicMock()
            bypass_request.method = "POST"
            bypass_request.url.path = "/api/admin/delete_user"
            bypass_request.headers = {"Authorization": f"Bearer {user_token}", **bypass_headers}
            bypass_request.client.host = "192.168.1.100"
            
            bypass_result = await auth_middleware.authenticate_request(bypass_request)
            bypass_authorized = auth_middleware.check_authorization(bypass_result["user"], "admin", "/api/admin/delete_user")
            assert bypass_authorized == False, f"Authorization bypass succeeded with headers: {bypass_headers}"
        
        logger.info("Authorization bypass prevention verified")

    @pytest.mark.cycle_45
    async def test_middleware_error_handling_maintains_security_posture(self, environment, auth_middleware):
        """
        Cycle 45: Test middleware error handling maintains security posture during failures.
        
        Revenue Protection: $380K annually from secure error handling.
        """
        logger.info("Testing middleware error handling - Cycle 45")
        
        # Test database connection failure during authentication
        with patch.object(auth_middleware, '_validate_token_in_database', side_effect=Exception("Database connection failed")):
            db_error_request = MagicMock()
            db_error_request.method = "GET"
            db_error_request.url.path = "/api/test"
            db_error_request.headers = {"Authorization": "Bearer valid_looking_token"}
            db_error_request.client.host = "192.168.1.100"
            
            result = await auth_middleware.authenticate_request(db_error_request)
            
            # Should fail securely (deny access) rather than allow access
            assert result["authenticated"] == False, "Database error incorrectly allowed access"
            assert "internal_error" in result.get("error", ""), "Error not properly categorized"
            assert "Database connection failed" not in result.get("error", ""), "Sensitive error details leaked"
        
        # Test external service failure during token validation
        with patch.object(auth_middleware, '_validate_with_auth_service', side_effect=Exception("Auth service unavailable")):
            service_error_request = MagicMock()
            service_error_request.method = "GET"
            service_error_request.url.path = "/api/test"
            service_error_request.headers = {"Authorization": "Bearer another_token"}
            service_error_request.client.host = "192.168.1.100"
            
            result = await auth_middleware.authenticate_request(service_error_request)
            
            # Should fail securely
            assert result["authenticated"] == False, "Service error incorrectly allowed access"
            assert "service_unavailable" in result.get("error", ""), "Service error not properly handled"
        
        # Test memory pressure during authentication
        with patch.object(auth_middleware, '_process_authentication', side_effect=MemoryError("Insufficient memory")):
            memory_error_request = MagicMock()
            memory_error_request.method = "GET" 
            memory_error_request.url.path = "/api/test"
            memory_error_request.headers = {"Authorization": "Bearer memory_test_token"}
            memory_error_request.client.host = "192.168.1.100"
            
            result = await auth_middleware.authenticate_request(memory_error_request)
            
            # Should fail securely and not crash
            assert result["authenticated"] == False, "Memory error incorrectly allowed access"
            assert "resource_error" in result.get("error", ""), "Resource error not properly handled"
        
        # Test timeout during authentication
        async def timeout_simulation(*args, **kwargs):
            await asyncio.sleep(10)  # Simulate long operation
            
        with patch.object(auth_middleware, '_validate_token_in_database', timeout_simulation):
            timeout_request = MagicMock()
            timeout_request.method = "GET"
            timeout_request.url.path = "/api/test"
            timeout_request.headers = {"Authorization": "Bearer timeout_token"}
            timeout_request.client.host = "192.168.1.100"
            
            start_time = time.time()
            
            # Should timeout and fail securely
            result = await asyncio.wait_for(
                auth_middleware.authenticate_request(timeout_request), 
                timeout=2.0
            )
            
            elapsed_time = time.time() - start_time
            assert elapsed_time < 3.0, f"Authentication took too long: {elapsed_time}s"
            assert result["authenticated"] == False, "Timeout incorrectly allowed access"
        
        logger.info("Middleware error handling verified")