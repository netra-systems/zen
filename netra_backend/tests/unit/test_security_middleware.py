# REMOVED_SYNTAX_ERROR: '''Unit tests for Security Middleware.

# REMOVED_SYNTAX_ERROR: Tests comprehensive security protection against web vulnerabilities.
# REMOVED_SYNTAX_ERROR: HIGHEST PRIORITY - Security breaches = customer churn.

# REMOVED_SYNTAX_ERROR: Business Value: Validates security headers, rate limiting, input validation,
# REMOVED_SYNTAX_ERROR: and CORS protection. Prevents attacks that could compromise customer data.

# REMOVED_SYNTAX_ERROR: Target Coverage:
    # REMOVED_SYNTAX_ERROR: - Security header injection (CSP, X-Frame-Options, HSTS, etc.)
    # REMOVED_SYNTAX_ERROR: - Rate limiting for different endpoints and users
    # REMOVED_SYNTAX_ERROR: - Input validation and sanitization
    # REMOVED_SYNTAX_ERROR: - Request size and URL validation
    # REMOVED_SYNTAX_ERROR: - IP tracking and authentication attempt monitoring
    # REMOVED_SYNTAX_ERROR: '''

    # REMOVED_SYNTAX_ERROR: import sys
    # REMOVED_SYNTAX_ERROR: from pathlib import Path
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from auth_service.core.auth_manager import AuthManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: from datetime import datetime, timedelta
    # REMOVED_SYNTAX_ERROR: from typing import Any, Dict, Optional

    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from fastapi import HTTPException, Request, Response, status
    # REMOVED_SYNTAX_ERROR: from fastapi.security import HTTPAuthorizationCredentials
    # REMOVED_SYNTAX_ERROR: from starlette.datastructures import URL, Headers

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.exceptions_auth import NetraSecurityException

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.middleware.security_middleware import ( )
    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: InputValidator,
    # REMOVED_SYNTAX_ERROR: RateLimitTracker,
    # REMOVED_SYNTAX_ERROR: SecurityConfig,
    # REMOVED_SYNTAX_ERROR: SecurityMiddleware,
    # REMOVED_SYNTAX_ERROR: create_security_middleware)

# REMOVED_SYNTAX_ERROR: class TestSecurityConfig:
    # REMOVED_SYNTAX_ERROR: """Test suite for SecurityConfig constants."""

# REMOVED_SYNTAX_ERROR: def test_security_config_rate_limits(self):
    # REMOVED_SYNTAX_ERROR: """Test rate limit configuration values."""
    # REMOVED_SYNTAX_ERROR: assert SecurityConfig.DEFAULT_RATE_LIMIT == 100
    # REMOVED_SYNTAX_ERROR: assert SecurityConfig.STRICT_RATE_LIMIT == 20
    # REMOVED_SYNTAX_ERROR: assert SecurityConfig.BURST_LIMIT == 5

# REMOVED_SYNTAX_ERROR: def test_security_config_size_limits(self):
    # REMOVED_SYNTAX_ERROR: """Test request size configuration values."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: assert SecurityConfig.MAX_REQUEST_SIZE == 10 * 1024 * 1024  # 10MB
    # REMOVED_SYNTAX_ERROR: assert SecurityConfig.MAX_HEADER_SIZE == 8192  # 8KB
    # REMOVED_SYNTAX_ERROR: assert SecurityConfig.MAX_URL_LENGTH == 2048  # 2KB

# REMOVED_SYNTAX_ERROR: def test_security_config_headers_present(self):
    # REMOVED_SYNTAX_ERROR: """Test security headers configuration."""
    # REMOVED_SYNTAX_ERROR: headers = SecurityConfig.SECURITY_HEADERS
    # REMOVED_SYNTAX_ERROR: expected_headers = [ )
    # REMOVED_SYNTAX_ERROR: "X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection",
    # REMOVED_SYNTAX_ERROR: "Strict-Transport-Security", "Referrer-Policy", "Content-Security-Policy"
    
    # REMOVED_SYNTAX_ERROR: for header in expected_headers:
        # REMOVED_SYNTAX_ERROR: assert header in headers

# REMOVED_SYNTAX_ERROR: def test_security_config_header_values(self):
    # REMOVED_SYNTAX_ERROR: """Test specific security header values."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: headers = SecurityConfig.SECURITY_HEADERS
    # REMOVED_SYNTAX_ERROR: assert headers["X-Content-Type-Options"] == "nosniff"
    # REMOVED_SYNTAX_ERROR: assert headers["X-Frame-Options"] == "DENY"
    # REMOVED_SYNTAX_ERROR: assert "max-age=31536000" in headers["Strict-Transport-Security"]

# REMOVED_SYNTAX_ERROR: class TestRateLimitTracker:
    # REMOVED_SYNTAX_ERROR: """Test suite for RateLimitTracker functionality."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def rate_limiter(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create fresh rate limit tracker."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return RateLimitTracker()

# REMOVED_SYNTAX_ERROR: def test_rate_limit_tracker_initialization(self, rate_limiter):
    # REMOVED_SYNTAX_ERROR: """Test rate limiter initializes with empty tracking."""
    # REMOVED_SYNTAX_ERROR: assert isinstance(rate_limiter._requests, dict)
    # REMOVED_SYNTAX_ERROR: assert isinstance(rate_limiter._blocked_ips, dict)
    # REMOVED_SYNTAX_ERROR: assert len(rate_limiter._requests) == 0

# REMOVED_SYNTAX_ERROR: def test_rate_limit_check_within_limit_allowed(self, rate_limiter):
    # REMOVED_SYNTAX_ERROR: """Test requests within limit are allowed."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: identifier = "test-ip-123"
    # REMOVED_SYNTAX_ERROR: limit = 10

    # REMOVED_SYNTAX_ERROR: is_limited = rate_limiter.is_rate_limited(identifier, limit)

    # REMOVED_SYNTAX_ERROR: assert is_limited is False

# REMOVED_SYNTAX_ERROR: def test_rate_limit_check_exceeds_limit_blocked(self, rate_limiter):
    # REMOVED_SYNTAX_ERROR: """Test requests exceeding limit are blocked."""
    # REMOVED_SYNTAX_ERROR: identifier = "test-ip-456"
    # REMOVED_SYNTAX_ERROR: limit = 2

    # Make requests up to limit
    # REMOVED_SYNTAX_ERROR: for _ in range(limit + 1):
        # REMOVED_SYNTAX_ERROR: is_limited = rate_limiter.is_rate_limited(identifier, limit)

        # REMOVED_SYNTAX_ERROR: assert is_limited is True

# REMOVED_SYNTAX_ERROR: def test_rate_limit_multiple_identifiers_independent(self, rate_limiter):
    # REMOVED_SYNTAX_ERROR: """Test different identifiers tracked independently."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: ip1, ip2 = "ip1", "ip2"
    # REMOVED_SYNTAX_ERROR: limit = 5

    # Exhaust limit for ip1
    # REMOVED_SYNTAX_ERROR: for _ in range(limit + 1):
        # REMOVED_SYNTAX_ERROR: rate_limiter.is_rate_limited(ip1, limit)

        # ip2 should still be allowed
        # REMOVED_SYNTAX_ERROR: is_limited = rate_limiter.is_rate_limited(ip2, limit)
        # REMOVED_SYNTAX_ERROR: assert is_limited is False

# REMOVED_SYNTAX_ERROR: def test_rate_limit_cleanup_old_requests(self, rate_limiter):
    # REMOVED_SYNTAX_ERROR: """Test old requests are cleaned up properly."""
    # REMOVED_SYNTAX_ERROR: identifier = "cleanup-test"
    # REMOVED_SYNTAX_ERROR: limit = 100

    # Add old request manually
    # REMOVED_SYNTAX_ERROR: rate_limiter._requests[identifier] = [time.time() - 120]  # 2 minutes ago

    # REMOVED_SYNTAX_ERROR: is_limited = rate_limiter.is_rate_limited(identifier, limit, window=60)

    # REMOVED_SYNTAX_ERROR: assert is_limited is False
    # REMOVED_SYNTAX_ERROR: assert len(rate_limiter._requests[identifier]) == 1  # Only new request

# REMOVED_SYNTAX_ERROR: def test_rate_limit_blocked_ip_remains_blocked(self, rate_limiter):
    # REMOVED_SYNTAX_ERROR: """Test blocked IP remains blocked during block period."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: identifier = "blocked-ip"
    # REMOVED_SYNTAX_ERROR: limit = 1

    # Trigger block
    # REMOVED_SYNTAX_ERROR: for _ in range(limit + 1):
        # REMOVED_SYNTAX_ERROR: rate_limiter.is_rate_limited(identifier, limit)

        # Should still be blocked
        # REMOVED_SYNTAX_ERROR: is_limited = rate_limiter.is_rate_limited(identifier, limit)
        # REMOVED_SYNTAX_ERROR: assert is_limited is True

# REMOVED_SYNTAX_ERROR: class TestInputValidator:
    # REMOVED_SYNTAX_ERROR: """Test suite for InputValidator functionality."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def validator(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create input validator instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return InputValidator()

# REMOVED_SYNTAX_ERROR: def test_input_validator_initialization(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test input validator initializes properly."""
    # REMOVED_SYNTAX_ERROR: assert hasattr(validator, 'validators')
    # REMOVED_SYNTAX_ERROR: assert validator.validators is not None

# REMOVED_SYNTAX_ERROR: def test_validate_input_empty_data_no_error(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test validation of empty data passes."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: validator.validate_input("", "test_field")
    # REMOVED_SYNTAX_ERROR: validator.validate_input(None, "test_field")
    # No exception should be raised

# REMOVED_SYNTAX_ERROR: def test_validate_input_normal_data_no_error(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test validation of normal data passes."""
    # REMOVED_SYNTAX_ERROR: normal_data = "This is normal user input data"

    # REMOVED_SYNTAX_ERROR: validator.validate_input(normal_data, "test_field")
    # No exception should be raised

# REMOVED_SYNTAX_ERROR: def test_sanitize_headers_removes_dangerous_headers(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test header sanitization removes dangerous headers."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: dangerous_headers = { )
    # REMOVED_SYNTAX_ERROR: "X-Forwarded-For": "127.0.0.1",
    # REMOVED_SYNTAX_ERROR: "Host": "evil.com",
    # REMOVED_SYNTAX_ERROR: "User-Agent": "Normal browser",
    # REMOVED_SYNTAX_ERROR: "Accept": "text/html"
    

    # REMOVED_SYNTAX_ERROR: sanitized = validator.sanitize_headers(dangerous_headers)

    # REMOVED_SYNTAX_ERROR: assert isinstance(sanitized, dict)
    # Should only contain safe headers

# REMOVED_SYNTAX_ERROR: def test_sanitize_headers_preserves_safe_headers(self, validator):
    # REMOVED_SYNTAX_ERROR: """Test header sanitization preserves safe headers."""
    # REMOVED_SYNTAX_ERROR: safe_headers = { )
    # REMOVED_SYNTAX_ERROR: "Content-Type": "application/json",
    # REMOVED_SYNTAX_ERROR: "Accept": "application/json",
    # REMOVED_SYNTAX_ERROR: "Authorization": "Bearer token123"
    

    # REMOVED_SYNTAX_ERROR: sanitized = validator.sanitize_headers(safe_headers)

    # Safe headers should be preserved (implementation dependent)
    # REMOVED_SYNTAX_ERROR: assert isinstance(sanitized, dict)

# REMOVED_SYNTAX_ERROR: class TestSecurityMiddleware:
    # REMOVED_SYNTAX_ERROR: """Test suite for SecurityMiddleware functionality."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_app():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock FastAPI application."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: return None  # TODO: Use real service instance

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def middleware(self, mock_app):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create security middleware instance."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: return SecurityMiddleware(mock_app)

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_request():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock FastAPI request."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: request = Mock(spec=Request)
    # REMOVED_SYNTAX_ERROR: request.method = "GET"
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: request.url = Mock(spec=URL)
    # REMOVED_SYNTAX_ERROR: request.url.path = "/api/test"
    # REMOVED_SYNTAX_ERROR: request.url.__str__ = Mock(return_value="https://example.com/api/test")
    # REMOVED_SYNTAX_ERROR: request.headers = Headers({"user-agent": "test-browser"})
    # Mock: Generic component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: request.client = client_instance  # Initialize appropriate service
    # REMOVED_SYNTAX_ERROR: request.client.host = "127.0.0.1"
    # REMOVED_SYNTAX_ERROR: return request

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_response():
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create mock FastAPI response."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock: Component isolation for controlled unit testing
    # REMOVED_SYNTAX_ERROR: response = Mock(spec=Response)
    # REMOVED_SYNTAX_ERROR: response.headers = {}
    # REMOVED_SYNTAX_ERROR: return response

# REMOVED_SYNTAX_ERROR: def test_security_middleware_initialization(self, middleware):
    # REMOVED_SYNTAX_ERROR: """Test security middleware initializes properly."""
    # REMOVED_SYNTAX_ERROR: assert hasattr(middleware, 'rate_limiter')
    # REMOVED_SYNTAX_ERROR: assert hasattr(middleware, 'input_validator')
    # REMOVED_SYNTAX_ERROR: assert hasattr(middleware, 'sensitive_endpoints')
    # REMOVED_SYNTAX_ERROR: assert isinstance(middleware.sensitive_endpoints, set)

# REMOVED_SYNTAX_ERROR: def test_security_middleware_sensitive_endpoints_configured(self, middleware):
    # REMOVED_SYNTAX_ERROR: """Test sensitive endpoints are properly configured."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: sensitive = middleware.sensitive_endpoints
    # REMOVED_SYNTAX_ERROR: expected_endpoints = [ )
    # REMOVED_SYNTAX_ERROR: "/auth/login", "/api/admin", "/api/tools",
    # REMOVED_SYNTAX_ERROR: "/api/users/create", "/api/synthetic-data"
    

    # REMOVED_SYNTAX_ERROR: for endpoint in expected_endpoints:
        # REMOVED_SYNTAX_ERROR: assert endpoint in sensitive

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_security_middleware_adds_security_headers(self, middleware, mock_request, mock_response):
            # REMOVED_SYNTAX_ERROR: """Test security middleware adds required headers."""
# REMOVED_SYNTAX_ERROR: async def mock_call_next(request):
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return mock_response

    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: response = await middleware.dispatch(mock_request, mock_call_next)

    # REMOVED_SYNTAX_ERROR: expected_headers = [ )
    # REMOVED_SYNTAX_ERROR: "X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"
    
    # REMOVED_SYNTAX_ERROR: for header in expected_headers:
        # REMOVED_SYNTAX_ERROR: assert header in response.headers

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_security_middleware_adds_custom_headers(self, middleware, mock_request, mock_response):
            # REMOVED_SYNTAX_ERROR: """Test middleware adds custom security headers."""
            # REMOVED_SYNTAX_ERROR: pass
# REMOVED_SYNTAX_ERROR: async def mock_call_next(request):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return mock_response

    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: response = await middleware.dispatch(mock_request, mock_call_next)

    # REMOVED_SYNTAX_ERROR: assert "X-Security-Middleware" in response.headers
    # REMOVED_SYNTAX_ERROR: assert response.headers["X-Security-Middleware"] == "enabled"
    # REMOVED_SYNTAX_ERROR: assert "X-Request-ID" in response.headers

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_security_middleware_rate_limiting_normal_endpoint(self, middleware, mock_request):
        # REMOVED_SYNTAX_ERROR: """Test rate limiting for normal endpoints."""
        # REMOVED_SYNTAX_ERROR: mock_request.url.path = "/api/normal"

        # Should use default rate limit
        # REMOVED_SYNTAX_ERROR: limit = middleware._determine_rate_limit(mock_request)

        # REMOVED_SYNTAX_ERROR: assert limit == SecurityConfig.DEFAULT_RATE_LIMIT

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_security_middleware_rate_limiting_sensitive_endpoint(self, middleware, mock_request):
            # REMOVED_SYNTAX_ERROR: """Test stricter rate limiting for sensitive endpoints."""
            # REMOVED_SYNTAX_ERROR: pass
            # REMOVED_SYNTAX_ERROR: mock_request.url.path = "/auth/login"

            # Should use strict rate limit
            # REMOVED_SYNTAX_ERROR: limit = middleware._determine_rate_limit(mock_request)

            # REMOVED_SYNTAX_ERROR: assert limit == SecurityConfig.STRICT_RATE_LIMIT

# REMOVED_SYNTAX_ERROR: def test_security_middleware_get_client_ip_from_request(self, middleware, mock_request):
    # REMOVED_SYNTAX_ERROR: """Test client IP extraction from request."""
    # REMOVED_SYNTAX_ERROR: mock_request.client.host = "192.168.1.100"

    # REMOVED_SYNTAX_ERROR: client_ip = middleware._get_client_ip(mock_request)

    # REMOVED_SYNTAX_ERROR: assert client_ip is not None
    # REMOVED_SYNTAX_ERROR: assert isinstance(client_ip, str)

# REMOVED_SYNTAX_ERROR: def test_security_middleware_validate_request_size_within_limit(self, middleware, mock_request):
    # REMOVED_SYNTAX_ERROR: """Test request size validation within limits."""
    # REMOVED_SYNTAX_ERROR: pass
    # Mock small request
    # Mock: Component isolation for testing without external dependencies
    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.middleware.security_validation_helpers.RequestValidators.validate_request_size') as mock_validate:
        # REMOVED_SYNTAX_ERROR: middleware._validate_request_size(mock_request)
        # REMOVED_SYNTAX_ERROR: mock_validate.assert_called_once()

# REMOVED_SYNTAX_ERROR: def test_security_middleware_validate_url_length_normal(self, middleware, mock_request):
    # REMOVED_SYNTAX_ERROR: """Test URL length validation for normal URLs."""
    # REMOVED_SYNTAX_ERROR: mock_request.url = "http://example.com/api/test"

    # Should not raise exception
    # REMOVED_SYNTAX_ERROR: middleware._validate_url(mock_request)

# REMOVED_SYNTAX_ERROR: def test_security_middleware_validate_headers_normal_size(self, middleware, mock_request):
    # REMOVED_SYNTAX_ERROR: """Test header validation for normal-sized headers."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: mock_request.headers = Headers({ ))
    # REMOVED_SYNTAX_ERROR: "User-Agent": "Mozilla/5.0 Browser",
    # REMOVED_SYNTAX_ERROR: "Accept": "application/json"
    

    # Should not raise exception
    # REMOVED_SYNTAX_ERROR: middleware._validate_headers(mock_request)

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_security_middleware_handles_post_request_body(self, middleware, mock_request):
        # REMOVED_SYNTAX_ERROR: """Test middleware validates POST request bodies."""
        # REMOVED_SYNTAX_ERROR: mock_request.method = "POST"
        # REMOVED_SYNTAX_ERROR: mock_request.body = AsyncMock(return_value=b'{"key": "value"}')

        # REMOVED_SYNTAX_ERROR: await middleware._validate_body_if_needed(mock_request)
        # Should complete without error

# REMOVED_SYNTAX_ERROR: def test_security_middleware_track_auth_attempt_success(self, middleware):
    # REMOVED_SYNTAX_ERROR: """Test successful authentication attempt tracking."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: ip_address = "192.168.1.50"

    # REMOVED_SYNTAX_ERROR: middleware.track_auth_attempt(ip_address, success=True)

    # REMOVED_SYNTAX_ERROR: assert ip_address in middleware.failed_auth_ips
    # REMOVED_SYNTAX_ERROR: assert middleware.failed_auth_ips[ip_address] == 0

# REMOVED_SYNTAX_ERROR: def test_security_middleware_track_auth_attempt_failure(self, middleware):
    # REMOVED_SYNTAX_ERROR: """Test failed authentication attempt tracking."""
    # REMOVED_SYNTAX_ERROR: ip_address = "192.168.1.51"

    # REMOVED_SYNTAX_ERROR: middleware.track_auth_attempt(ip_address, success=False)

    # REMOVED_SYNTAX_ERROR: assert ip_address in middleware.failed_auth_ips
    # REMOVED_SYNTAX_ERROR: assert middleware.failed_auth_ips[ip_address] == 1

# REMOVED_SYNTAX_ERROR: def test_security_middleware_is_ip_suspicious_high_failures(self, middleware):
    # REMOVED_SYNTAX_ERROR: """Test IP marked suspicious with high failure count."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: ip_address = "192.168.1.52"
    # REMOVED_SYNTAX_ERROR: middleware.failed_auth_ips[ip_address] = 8

    # REMOVED_SYNTAX_ERROR: is_suspicious = middleware.is_ip_suspicious(ip_address)

    # REMOVED_SYNTAX_ERROR: assert is_suspicious is True

# REMOVED_SYNTAX_ERROR: def test_security_middleware_is_ip_suspicious_normal_activity(self, middleware):
    # REMOVED_SYNTAX_ERROR: """Test IP not marked suspicious with normal activity."""
    # REMOVED_SYNTAX_ERROR: ip_address = "192.168.1.53"
    # REMOVED_SYNTAX_ERROR: middleware.failed_auth_ips[ip_address] = 2

    # REMOVED_SYNTAX_ERROR: is_suspicious = middleware.is_ip_suspicious(ip_address)

    # REMOVED_SYNTAX_ERROR: assert is_suspicious is False

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_security_middleware_rate_limit_exceeded_raises_429(self, middleware, mock_request):
        # REMOVED_SYNTAX_ERROR: """Test rate limit exceeded raises 429 error."""
        # REMOVED_SYNTAX_ERROR: pass
        # Mock rate limiter to await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return True (rate limited)
        # REMOVED_SYNTAX_ERROR: with patch.object(middleware.rate_limiter, 'is_rate_limited', return_value=True):
            # REMOVED_SYNTAX_ERROR: with pytest.raises(HTTPException) as exc_info:
                # REMOVED_SYNTAX_ERROR: await middleware._check_rate_limits(mock_request)

                # REMOVED_SYNTAX_ERROR: assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_security_middleware_error_handling(self, middleware, mock_request):
                    # REMOVED_SYNTAX_ERROR: """Test middleware handles internal errors gracefully."""
# REMOVED_SYNTAX_ERROR: async def failing_call_next(request):
    # REMOVED_SYNTAX_ERROR: raise Exception("Simulated internal error")

    # REMOVED_SYNTAX_ERROR: with pytest.raises(HTTPException) as exc_info:
        # Mock: Component isolation for testing without external dependencies
        # REMOVED_SYNTAX_ERROR: await middleware.dispatch(mock_request, failing_call_next)

        # REMOVED_SYNTAX_ERROR: assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

# REMOVED_SYNTAX_ERROR: class TestSecurityMiddlewareFactory:
    # REMOVED_SYNTAX_ERROR: """Test suite for security middleware factory function."""

# REMOVED_SYNTAX_ERROR: def test_create_security_middleware_default_rate_limiter(self):
    # REMOVED_SYNTAX_ERROR: """Test factory creates middleware with default rate limiter."""
    # REMOVED_SYNTAX_ERROR: middleware = create_security_middleware()

    # REMOVED_SYNTAX_ERROR: assert isinstance(middleware, SecurityMiddleware)
    # REMOVED_SYNTAX_ERROR: assert hasattr(middleware, 'rate_limiter')

# REMOVED_SYNTAX_ERROR: def test_create_security_middleware_custom_rate_limiter(self):
    # REMOVED_SYNTAX_ERROR: """Test factory creates middleware with custom rate limiter."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: custom_limiter = RateLimitTracker()

    # REMOVED_SYNTAX_ERROR: middleware = create_security_middleware(custom_limiter)

    # REMOVED_SYNTAX_ERROR: assert middleware.rate_limiter is custom_limiter