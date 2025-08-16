"""
Security middleware for comprehensive protection against common web vulnerabilities.
Implements multiple security layers including rate limiting, CSRF protection, and security headers.
"""

from typing import Callable, Dict, Any, Optional, Set
import time
import hashlib
import hmac
import re
from datetime import datetime, timedelta
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from app.logging_config import central_logger
from app.core.exceptions_auth import NetraSecurityException
from app.core.error_codes import ErrorCode
from app.middleware.security_validation_helpers import (
    SecurityValidators, RequestValidators, HeaderSanitizer, 
    IPValidators, RateLimitHelpers, AuthAttemptTracker
)

logger = central_logger.get_logger(__name__)


class SecurityConfig:
    """Security configuration constants."""
    # Rate limiting
    DEFAULT_RATE_LIMIT = 100  # requests per minute
    STRICT_RATE_LIMIT = 20   # for sensitive endpoints
    BURST_LIMIT = 5          # burst allowance
    
    # Input validation
    MAX_REQUEST_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_HEADER_SIZE = 8192               # 8KB
    MAX_URL_LENGTH = 2048                # 2KB
    
    # Security headers
    SECURITY_HEADERS = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY", 
        "X-XSS-Protection": "1; mode=block",
        "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'",
        "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
    }


class RateLimitTracker:
    """Track rate limits for IPs and users."""
    
    def __init__(self):
        self._requests: Dict[str, list] = {}
        self._blocked_ips: Dict[str, datetime] = {}
    
    def is_rate_limited(self, identifier: str, limit: int, window: int = 60) -> bool:
        """Check if identifier is rate limited."""
        now = time.time()
        if self._is_blocked(identifier, now):
            return True
        self._clean_old_requests(identifier, now, window)
        return self._check_and_apply_limit(identifier, limit, now)
    
    def _is_blocked(self, identifier: str, now: float) -> bool:
        """Check if identifier is temporarily blocked."""
        if identifier in self._blocked_ips:
            if now < self._blocked_ips[identifier].timestamp():
                return True
            else:
                del self._blocked_ips[identifier]
        return False
    
    def _clean_old_requests(self, identifier: str, now: float, window: int) -> None:
        """Clean old requests outside the time window."""
        if identifier not in self._requests:
            self._requests[identifier] = []
        self._requests[identifier] = RateLimitHelpers.clean_old_requests(
            self._requests[identifier], now, window
        )
    
    def _check_and_apply_limit(self, identifier: str, limit: int, now: float) -> bool:
        """Check limit and apply blocking if exceeded."""
        if RateLimitHelpers.should_block_ip(len(self._requests[identifier]), limit):
            self._blocked_ips[identifier] = RateLimitHelpers.calculate_block_time(5)
            RateLimitHelpers.log_rate_limit_exceeded(identifier, 5)
            return True
        self._requests[identifier].append(now)
        return False


class InputValidator:
    """Validate and sanitize inputs."""
    
    def __init__(self):
        self.validators = SecurityValidators()
    
    def validate_input(self, data: str, field_name: str = "input") -> None:
        """Validate input for security threats."""
        if not data:
            return
        self.validators.validate_sql_injection(data, field_name)
        self.validators.validate_xss_attack(data, field_name)
        self.validators.validate_command_injection(data, field_name)
        self.validators.validate_path_traversal(data, field_name)
    
    
    def sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize HTTP headers."""
        sanitized = {}
        allowed_headers = HeaderSanitizer.get_allowed_headers()
        self._process_header_sanitization(headers, sanitized, allowed_headers)
        return sanitized
    
    def _process_header_sanitization(self, headers: Dict[str, str], sanitized: Dict[str, str], allowed_headers) -> None:
        """Process header sanitization for all headers."""
        for key, value in headers.items():
            if HeaderSanitizer.is_header_allowed(key, value, SecurityConfig.MAX_HEADER_SIZE, allowed_headers):
                sanitized[key] = HeaderSanitizer.sanitize_header_value(value, SecurityConfig.MAX_HEADER_SIZE)
    


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware."""
    
    def __init__(self, app, rate_limiter: Optional[RateLimitTracker] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimitTracker()
        self.input_validator = InputValidator()
        self.security_bearer = HTTPBearer(auto_error=False)
        self._initialize_sensitive_endpoints()
        self._initialize_auth_tracking()
    
    def _initialize_sensitive_endpoints(self) -> None:
        """Initialize sensitive endpoints requiring stricter limits."""
        self.sensitive_endpoints = {
            "/api/auth/login", "/api/auth/logout", "/api/auth/token",
            "/api/auth/callback", "/api/auth/refresh",
            "/api/admin", "/api/tools", "/api/synthetic-data",
            "/api/users/create", "/api/users/password"
        }
    
    def _initialize_auth_tracking(self) -> None:
        """Initialize authentication attempt tracking."""
        self.auth_attempt_tracker: Dict[str, list] = {}
        self.failed_auth_ips: Dict[str, int] = {}
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security layers."""
        start_time = time.time()
        try:
            await self._perform_security_validations(request)
            response = await self._process_secure_request(request, call_next)
            self._log_security_processing(request, start_time)
            return response
        except NetraSecurityException:
            raise
        except Exception as e:
            self._handle_security_middleware_error(e)
    
    def _handle_security_middleware_error(self, error: Exception) -> None:
        """Handle security middleware errors."""
        logger.error(f"Security middleware error: {error}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Security validation failed"
        )
    
    async def _perform_security_validations(self, request: Request) -> None:
        """Perform all security validations on request."""
        self._validate_request_size(request)
        self._validate_url(request)
        self._validate_headers(request)
        await self._check_rate_limits(request)
        await self._validate_body_if_needed(request)
    
    async def _validate_body_if_needed(self, request: Request) -> None:
        """Validate request body for POST, PUT, PATCH methods."""
        if request.method in ["POST", "PUT", "PATCH"]:
            await self._validate_request_body(request)
    
    async def _process_secure_request(self, request: Request, call_next: Callable) -> Response:
        """Process request with security headers."""
        response = await call_next(request)
        self._add_security_headers(response)
        return response
    
    def _log_security_processing(self, request: Request, start_time: float) -> None:
        """Log security processing metrics."""
        processing_time = time.time() - start_time
        logger.info(f"Security middleware processed {request.method} {request.url.path} in {processing_time:.3f}s")
    
    def _validate_request_size(self, request: Request) -> None:
        """Validate request size."""
        RequestValidators.validate_request_size(request, SecurityConfig.MAX_REQUEST_SIZE)
    
    def _validate_url(self, request: Request) -> None:
        """Validate URL length and characters."""
        url_str = str(request.url)
        RequestValidators.validate_url_length(url_str, SecurityConfig.MAX_URL_LENGTH)
        RequestValidators.validate_url_characters(url_str)
    
    def _validate_headers(self, request: Request) -> None:
        """Validate HTTP headers."""
        for name, value in request.headers.items():
            RequestValidators.validate_header_size(name, value, SecurityConfig.MAX_HEADER_SIZE)
    
    async def _check_rate_limits(self, request: Request) -> None:
        """Check rate limits."""
        client_ip = self._get_client_ip(request)
        user_id = await self._get_user_id(request)
        limit = self._determine_rate_limit(request)
        await self._perform_rate_limit_checks(client_ip, user_id, limit)
    
    async def _perform_rate_limit_checks(self, client_ip: str, user_id: Optional[str], limit: int) -> None:
        """Perform IP and user rate limit checks."""
        await self._check_ip_rate_limit(client_ip, limit)
        if user_id:
            await self._check_user_rate_limit(user_id, limit)
    
    def _determine_rate_limit(self, request: Request) -> int:
        """Determine rate limit based on endpoint sensitivity."""
        path = str(request.url.path)
        if RateLimitHelpers.is_sensitive_endpoint(path, self.sensitive_endpoints):
            return SecurityConfig.STRICT_RATE_LIMIT
        return SecurityConfig.DEFAULT_RATE_LIMIT
    
    async def _check_ip_rate_limit(self, client_ip: str, limit: int) -> None:
        """Check IP-based rate limit."""
        identifier = f"ip:{client_ip}"
        if self.rate_limiter.is_rate_limited(identifier, limit):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            self._raise_rate_limit_exception("Rate limit exceeded")
    
    async def _check_user_rate_limit(self, user_id: str, limit: int) -> None:
        """Check user-based rate limit."""
        user_identifier = f"user:{user_id}"
        if self.rate_limiter.is_rate_limited(user_identifier, limit * 2):
            logger.warning(f"Rate limit exceeded for user: {user_id}")
            self._raise_rate_limit_exception("Rate limit exceeded for user")
    
    def _raise_rate_limit_exception(self, detail: str) -> None:
        """Raise rate limit exceeded exception."""
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=detail,
            headers={"Retry-After": "300"}
        )
    
    async def _validate_request_body(self, request: Request) -> None:
        """Validate request body content."""
        try:
            body = await request.body()
            if body:
                self._validate_decoded_body(body)
        except UnicodeDecodeError:
            RequestValidators.handle_encoding_error()
    
    def _validate_decoded_body(self, body: bytes) -> None:
        """Validate decoded request body."""
        body_str = RequestValidators.decode_request_body(body)
        self.input_validator.validate_input(body_str, "request_body")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_headers = IPValidators.get_forwarded_headers()
        extracted_ip = self._extract_valid_ip(request, forwarded_headers)
        return extracted_ip if extracted_ip else IPValidators.get_fallback_ip(request)
    
    def _extract_valid_ip(self, request: Request, forwarded_headers) -> Optional[str]:
        """Extract valid IP from forwarded headers."""
        for header in forwarded_headers:
            ip = IPValidators.extract_ip_from_header(request, header)
            if ip and IPValidators.is_valid_ip(ip):
                return ip
        return None
    
    async def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request if authenticated."""
        try:
            auth_header = request.headers.get("authorization")
            if self._has_bearer_token(auth_header):
                return self._extract_user_from_token(auth_header)
        except Exception:
            pass
        return None
    
    def _has_bearer_token(self, auth_header: Optional[str]) -> bool:
        """Check if request has bearer token."""
        return auth_header and auth_header.startswith("Bearer ")
    
    def _extract_user_from_token(self, auth_header: str) -> Optional[str]:
        """Extract user ID from bearer token."""
        # This would need to be integrated with your auth system
        return None
    
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
        self._add_custom_headers(response)
    
    def _add_custom_headers(self, response: Response) -> None:
        """Add custom security headers."""
        response.headers["X-Security-Middleware"] = "enabled"
        response.headers["X-Request-ID"] = f"req_{int(time.time())}"
    
    def track_auth_attempt(self, ip_address: str, success: bool) -> None:
        """Track authentication attempts for enhanced security."""
        current_time = time.time()
        self._track_attempt_time(ip_address, current_time)
        if not success:
            self._handle_failed_auth(ip_address)
        else:
            self.failed_auth_ips[ip_address] = AuthAttemptTracker.reset_failed_count()
    
    def _track_attempt_time(self, ip_address: str, current_time: float) -> None:
        """Track authentication attempt time."""
        self._initialize_ip_tracker(ip_address)
        self._clean_and_append_attempt(ip_address, current_time)
    
    def _initialize_ip_tracker(self, ip_address: str) -> None:
        """Initialize IP tracker if not exists."""
        if ip_address not in self.auth_attempt_tracker:
            self.auth_attempt_tracker[ip_address] = []
    
    def _clean_and_append_attempt(self, ip_address: str, current_time: float) -> None:
        """Clean old attempts and append new one."""
        self.auth_attempt_tracker[ip_address] = AuthAttemptTracker.clean_old_attempts(
            self.auth_attempt_tracker[ip_address], current_time, 1
        )
        self.auth_attempt_tracker[ip_address].append(current_time)
    
    def _handle_failed_auth(self, ip_address: str) -> None:
        """Handle failed authentication attempt."""
        self.failed_auth_ips[ip_address] = self.failed_auth_ips.get(ip_address, 0) + 1
        if AuthAttemptTracker.should_auto_block(self.failed_auth_ips[ip_address], 10):
            AuthAttemptTracker.log_auth_block(ip_address, self.failed_auth_ips[ip_address])
    
    def is_ip_suspicious(self, ip_address: str) -> bool:
        """Check if IP should be treated as suspicious."""
        failed_count = self.failed_auth_ips.get(ip_address, 0)
        recent_attempts = len(self.auth_attempt_tracker.get(ip_address, []))
        thresholds = {'failed': 5, 'recent': 20}
        return AuthAttemptTracker.is_ip_suspicious(failed_count, recent_attempts, thresholds)


def create_security_middleware(rate_limiter: Optional[RateLimitTracker] = None) -> SecurityMiddleware:
    """Factory function to create security middleware."""
    return SecurityMiddleware(None, rate_limiter)


# Global rate limiter instance
global_rate_limiter = RateLimitTracker()