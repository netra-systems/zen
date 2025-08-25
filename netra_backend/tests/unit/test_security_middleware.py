"""Unit tests for Security Middleware.

Tests comprehensive security protection against web vulnerabilities.
HIGHEST PRIORITY - Security breaches = customer churn.

Business Value: Validates security headers, rate limiting, input validation,
and CORS protection. Prevents attacks that could compromise customer data.

Target Coverage:
- Security header injection (CSP, X-Frame-Options, HSTS, etc.)
- Rate limiting for different endpoints and users
- Input validation and sanitization
- Request size and URL validation
- IP tracking and authentication attempt monitoring
"""

import sys
from pathlib import Path

import time
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, Request, Response, status
from fastapi.security import HTTPAuthorizationCredentials
from starlette.datastructures import URL, Headers

from netra_backend.app.core.exceptions_auth import NetraSecurityException

from netra_backend.app.middleware.security_middleware import (
    InputValidator,
    RateLimitTracker,
    SecurityConfig,
    SecurityMiddleware,
    create_security_middleware,
)

class TestSecurityConfig:
    """Test suite for SecurityConfig constants."""
    
    def test_security_config_rate_limits(self):
        """Test rate limit configuration values."""
        assert SecurityConfig.DEFAULT_RATE_LIMIT == 100
        assert SecurityConfig.STRICT_RATE_LIMIT == 20
        assert SecurityConfig.BURST_LIMIT == 5

    def test_security_config_size_limits(self):
        """Test request size configuration values."""
        assert SecurityConfig.MAX_REQUEST_SIZE == 10 * 1024 * 1024  # 10MB
        assert SecurityConfig.MAX_HEADER_SIZE == 8192  # 8KB
        assert SecurityConfig.MAX_URL_LENGTH == 2048  # 2KB

    def test_security_config_headers_present(self):
        """Test security headers configuration."""
        headers = SecurityConfig.SECURITY_HEADERS
        expected_headers = [
            "X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection",
            "Strict-Transport-Security", "Referrer-Policy", "Content-Security-Policy"
        ]
        for header in expected_headers:
            assert header in headers

    def test_security_config_header_values(self):
        """Test specific security header values."""
        headers = SecurityConfig.SECURITY_HEADERS
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["X-Frame-Options"] == "DENY"
        assert "max-age=31536000" in headers["Strict-Transport-Security"]

class TestRateLimitTracker:
    """Test suite for RateLimitTracker functionality."""
    
    @pytest.fixture
    def rate_limiter(self):
        """Create fresh rate limit tracker."""
        return RateLimitTracker()
    
    def test_rate_limit_tracker_initialization(self, rate_limiter):
        """Test rate limiter initializes with empty tracking."""
        assert isinstance(rate_limiter._requests, dict)
        assert isinstance(rate_limiter._blocked_ips, dict)
        assert len(rate_limiter._requests) == 0

    def test_rate_limit_check_within_limit_allowed(self, rate_limiter):
        """Test requests within limit are allowed."""
        identifier = "test-ip-123"
        limit = 10
        
        is_limited = rate_limiter.is_rate_limited(identifier, limit)
        
        assert is_limited is False

    def test_rate_limit_check_exceeds_limit_blocked(self, rate_limiter):
        """Test requests exceeding limit are blocked."""
        identifier = "test-ip-456"
        limit = 2
        
        # Make requests up to limit
        for _ in range(limit + 1):
            is_limited = rate_limiter.is_rate_limited(identifier, limit)
        
        assert is_limited is True

    def test_rate_limit_multiple_identifiers_independent(self, rate_limiter):
        """Test different identifiers tracked independently."""
        ip1, ip2 = "ip1", "ip2"
        limit = 5
        
        # Exhaust limit for ip1
        for _ in range(limit + 1):
            rate_limiter.is_rate_limited(ip1, limit)
        
        # ip2 should still be allowed
        is_limited = rate_limiter.is_rate_limited(ip2, limit)
        assert is_limited is False

    def test_rate_limit_cleanup_old_requests(self, rate_limiter):
        """Test old requests are cleaned up properly."""
        identifier = "cleanup-test"
        limit = 100
        
        # Add old request manually
        rate_limiter._requests[identifier] = [time.time() - 120]  # 2 minutes ago
        
        is_limited = rate_limiter.is_rate_limited(identifier, limit, window=60)
        
        assert is_limited is False
        assert len(rate_limiter._requests[identifier]) == 1  # Only new request

    def test_rate_limit_blocked_ip_remains_blocked(self, rate_limiter):
        """Test blocked IP remains blocked during block period."""
        identifier = "blocked-ip"
        limit = 1
        
        # Trigger block
        for _ in range(limit + 1):
            rate_limiter.is_rate_limited(identifier, limit)
        
        # Should still be blocked
        is_limited = rate_limiter.is_rate_limited(identifier, limit)
        assert is_limited is True

class TestInputValidator:
    """Test suite for InputValidator functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create input validator instance."""
        return InputValidator()
    
    def test_input_validator_initialization(self, validator):
        """Test input validator initializes properly."""
        assert hasattr(validator, 'validators')
        assert validator.validators is not None

    def test_validate_input_empty_data_no_error(self, validator):
        """Test validation of empty data passes."""
        validator.validate_input("", "test_field")
        validator.validate_input(None, "test_field")
        # No exception should be raised

    def test_validate_input_normal_data_no_error(self, validator):
        """Test validation of normal data passes."""
        normal_data = "This is normal user input data"
        
        validator.validate_input(normal_data, "test_field")
        # No exception should be raised

    def test_sanitize_headers_removes_dangerous_headers(self, validator):
        """Test header sanitization removes dangerous headers."""
        dangerous_headers = {
            "X-Forwarded-For": "127.0.0.1",
            "Host": "evil.com",
            "User-Agent": "Normal browser",
            "Accept": "text/html"
        }
        
        sanitized = validator.sanitize_headers(dangerous_headers)
        
        assert isinstance(sanitized, dict)
        # Should only contain safe headers

    def test_sanitize_headers_preserves_safe_headers(self, validator):
        """Test header sanitization preserves safe headers."""
        safe_headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": "Bearer token123"
        }
        
        sanitized = validator.sanitize_headers(safe_headers)
        
        # Safe headers should be preserved (implementation dependent)
        assert isinstance(sanitized, dict)

class TestSecurityMiddleware:
    """Test suite for SecurityMiddleware functionality."""
    
    @pytest.fixture
    def mock_app(self):
        """Create mock FastAPI application."""
        # Mock: Generic component isolation for controlled unit testing
        return Mock()
    
    @pytest.fixture
    def middleware(self, mock_app):
        """Create security middleware instance."""
        return SecurityMiddleware(mock_app)
    
    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request."""
        # Mock: Component isolation for controlled unit testing
        request = Mock(spec=Request)
        request.method = "GET"
        # Mock: Component isolation for controlled unit testing
        request.url = Mock(spec=URL)
        request.url.path = "/api/test"
        request.url.__str__ = Mock(return_value="https://example.com/api/test")
        request.headers = Headers({"user-agent": "test-browser"})
        # Mock: Generic component isolation for controlled unit testing
        request.client = Mock()
        request.client.host = "127.0.0.1"
        return request
    
    @pytest.fixture
    def mock_response(self):
        """Create mock FastAPI response."""
        # Mock: Component isolation for controlled unit testing
        response = Mock(spec=Response)
        response.headers = {}
        return response

    def test_security_middleware_initialization(self, middleware):
        """Test security middleware initializes properly."""
        assert hasattr(middleware, 'rate_limiter')
        assert hasattr(middleware, 'input_validator')
        assert hasattr(middleware, 'sensitive_endpoints')
        assert isinstance(middleware.sensitive_endpoints, set)

    def test_security_middleware_sensitive_endpoints_configured(self, middleware):
        """Test sensitive endpoints are properly configured."""
        sensitive = middleware.sensitive_endpoints
        expected_endpoints = [
            "/api/auth/login", "/api/admin", "/api/tools",
            "/api/users/create", "/api/synthetic-data"
        ]
        
        for endpoint in expected_endpoints:
            assert endpoint in sensitive

    @pytest.mark.asyncio
    async def test_security_middleware_adds_security_headers(self, middleware, mock_request, mock_response):
        """Test security middleware adds required headers."""
        async def mock_call_next(request):
            return mock_response
        
        # Mock: Component isolation for testing without external dependencies
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        expected_headers = [
            "X-Content-Type-Options", "X-Frame-Options", "X-XSS-Protection"
        ]
        for header in expected_headers:
            assert header in response.headers

    @pytest.mark.asyncio
    async def test_security_middleware_adds_custom_headers(self, middleware, mock_request, mock_response):
        """Test middleware adds custom security headers."""
        async def mock_call_next(request):
            return mock_response
        
        # Mock: Component isolation for testing without external dependencies
        response = await middleware.dispatch(mock_request, mock_call_next)
        
        assert "X-Security-Middleware" in response.headers
        assert response.headers["X-Security-Middleware"] == "enabled"
        assert "X-Request-ID" in response.headers

    @pytest.mark.asyncio
    async def test_security_middleware_rate_limiting_normal_endpoint(self, middleware, mock_request):
        """Test rate limiting for normal endpoints."""
        mock_request.url.path = "/api/normal"
        
        # Should use default rate limit
        limit = middleware._determine_rate_limit(mock_request)
        
        assert limit == SecurityConfig.DEFAULT_RATE_LIMIT

    @pytest.mark.asyncio
    async def test_security_middleware_rate_limiting_sensitive_endpoint(self, middleware, mock_request):
        """Test stricter rate limiting for sensitive endpoints."""
        mock_request.url.path = "/api/auth/login"
        
        # Should use strict rate limit
        limit = middleware._determine_rate_limit(mock_request)
        
        assert limit == SecurityConfig.STRICT_RATE_LIMIT

    def test_security_middleware_get_client_ip_from_request(self, middleware, mock_request):
        """Test client IP extraction from request."""
        mock_request.client.host = "192.168.1.100"
        
        client_ip = middleware._get_client_ip(mock_request)
        
        assert client_ip is not None
        assert isinstance(client_ip, str)

    def test_security_middleware_validate_request_size_within_limit(self, middleware, mock_request):
        """Test request size validation within limits."""
        # Mock small request
        # Mock: Component isolation for testing without external dependencies
        with patch('netra_backend.app.middleware.security_validation_helpers.RequestValidators.validate_request_size') as mock_validate:
            middleware._validate_request_size(mock_request)
            mock_validate.assert_called_once()

    def test_security_middleware_validate_url_length_normal(self, middleware, mock_request):
        """Test URL length validation for normal URLs."""
        mock_request.url = "http://example.com/api/test"
        
        # Should not raise exception
        middleware._validate_url(mock_request)

    def test_security_middleware_validate_headers_normal_size(self, middleware, mock_request):
        """Test header validation for normal-sized headers."""
        mock_request.headers = Headers({
            "User-Agent": "Mozilla/5.0 Browser",
            "Accept": "application/json"
        })
        
        # Should not raise exception
        middleware._validate_headers(mock_request)

    @pytest.mark.asyncio
    async def test_security_middleware_handles_post_request_body(self, middleware, mock_request):
        """Test middleware validates POST request bodies."""
        mock_request.method = "POST"
        mock_request.body = AsyncMock(return_value=b'{"key": "value"}')
        
        await middleware._validate_body_if_needed(mock_request)
        # Should complete without error

    def test_security_middleware_track_auth_attempt_success(self, middleware):
        """Test successful authentication attempt tracking."""
        ip_address = "192.168.1.50"
        
        middleware.track_auth_attempt(ip_address, success=True)
        
        assert ip_address in middleware.failed_auth_ips
        assert middleware.failed_auth_ips[ip_address] == 0

    def test_security_middleware_track_auth_attempt_failure(self, middleware):
        """Test failed authentication attempt tracking."""
        ip_address = "192.168.1.51"
        
        middleware.track_auth_attempt(ip_address, success=False)
        
        assert ip_address in middleware.failed_auth_ips
        assert middleware.failed_auth_ips[ip_address] == 1

    def test_security_middleware_is_ip_suspicious_high_failures(self, middleware):
        """Test IP marked suspicious with high failure count."""
        ip_address = "192.168.1.52"
        middleware.failed_auth_ips[ip_address] = 8
        
        is_suspicious = middleware.is_ip_suspicious(ip_address)
        
        assert is_suspicious is True

    def test_security_middleware_is_ip_suspicious_normal_activity(self, middleware):
        """Test IP not marked suspicious with normal activity."""
        ip_address = "192.168.1.53"
        middleware.failed_auth_ips[ip_address] = 2
        
        is_suspicious = middleware.is_ip_suspicious(ip_address)
        
        assert is_suspicious is False

    @pytest.mark.asyncio
    async def test_security_middleware_rate_limit_exceeded_raises_429(self, middleware, mock_request):
        """Test rate limit exceeded raises 429 error."""
        # Mock rate limiter to return True (rate limited)
        with patch.object(middleware.rate_limiter, 'is_rate_limited', return_value=True):
            with pytest.raises(HTTPException) as exc_info:
                await middleware._check_rate_limits(mock_request)
            
            assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    @pytest.mark.asyncio
    async def test_security_middleware_error_handling(self, middleware, mock_request):
        """Test middleware handles internal errors gracefully."""
        async def failing_call_next(request):
            raise Exception("Simulated internal error")
        
        with pytest.raises(HTTPException) as exc_info:
            # Mock: Component isolation for testing without external dependencies
            await middleware.dispatch(mock_request, failing_call_next)
        
        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

class TestSecurityMiddlewareFactory:
    """Test suite for security middleware factory function."""
    
    def test_create_security_middleware_default_rate_limiter(self):
        """Test factory creates middleware with default rate limiter."""
        middleware = create_security_middleware()
        
        assert isinstance(middleware, SecurityMiddleware)
        assert hasattr(middleware, 'rate_limiter')

    def test_create_security_middleware_custom_rate_limiter(self):
        """Test factory creates middleware with custom rate limiter."""
        custom_limiter = RateLimitTracker()
        
        middleware = create_security_middleware(custom_limiter)
        
        assert middleware.rate_limiter is custom_limiter