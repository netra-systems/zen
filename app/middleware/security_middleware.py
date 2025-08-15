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
        
        self._requests[identifier] = [
            req_time for req_time in self._requests[identifier] 
            if now - req_time < window
        ]
    
    def _check_and_apply_limit(self, identifier: str, limit: int, now: float) -> bool:
        """Check limit and apply blocking if exceeded."""
        if len(self._requests[identifier]) >= limit:
            self._blocked_ips[identifier] = datetime.now() + timedelta(minutes=5)
            logger.warning(f"Rate limit exceeded for {identifier}, blocking for 5 minutes")
            return True
        
        self._requests[identifier].append(now)
        return False


class InputValidator:
    """Validate and sanitize inputs."""
    
    # Enhanced dangerous patterns to block
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION|GRANT|REVOKE)\b)',
        r'(-{2}|/\*|\*/)',  # SQL comments
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',  # OR 1=1, AND 1=1
        r'(\bxp_cmdshell\b)',  # SQL Server command execution
        r'(\bsp_executesql\b)',  # SQL Server stored procedure
        r'(\bINTO\s+OUTFILE\b)',  # MySQL file operations
        r'(\bLOAD_FILE\b)',  # MySQL file reading
        r'(\bUNION\s+ALL\s+SELECT\b)',  # UNION injection
        r'(\bINFORMATION_SCHEMA\b)',  # Schema enumeration
        r'(\bSYS\.\b)',  # System table access
    ]
    
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # event handlers
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
        r'<form[^>]*>',  # unauthorized forms
        r'<input[^>]*>',  # unauthorized inputs
        r'vbscript:',  # VBScript
        r'data:text/html',  # Data URLs with HTML
        r'expression\s*\(',  # CSS expressions
        r'@import',  # CSS imports
        r'<link[^>]*>',  # unauthorized stylesheets
    ]
    
    COMMAND_INJECTION_PATTERNS = [
        r'(\||\||&|&&|;|`)',  # Command separators
        r'(\$\(|\`)',  # Command substitution
        r'(\bwget\b|\bcurl\b|\bpowershell\b|\bcmd\b|\bsh\b|\bbash\b)',
        r'(\brm\s+|\bdel\s+|\brmdir\b)',  # File deletion
        r'(\bcat\s+|\btype\s+)',  # File reading
        r'(\bchmod\b|\bchown\b)',  # Permission changes
    ]
    
    PATH_TRAVERSAL_PATTERNS = [
        r'\.\./',  # Directory traversal
        r'\.\.\\\\',  # Windows directory traversal
        r'%2e%2e%2f',  # URL encoded traversal
        r'%2e%2e\/',  # Mixed encoding
        r'/etc/passwd',  # Common target files
        r'/windows/system32',
        r'C:\\',  # Windows paths
    ]
    
    def __init__(self):
        self.sql_regex = re.compile('|'.join(self.SQL_INJECTION_PATTERNS), re.IGNORECASE)
        self.xss_regex = re.compile('|'.join(self.XSS_PATTERNS), re.IGNORECASE)
        self.command_regex = re.compile('|'.join(self.COMMAND_INJECTION_PATTERNS), re.IGNORECASE)
        self.path_regex = re.compile('|'.join(self.PATH_TRAVERSAL_PATTERNS), re.IGNORECASE)
    
    def validate_input(self, data: str, field_name: str = "input") -> None:
        """Validate input for security threats."""
        if not data:
            return
        
        self._check_sql_injection(data, field_name)
        self._check_xss_attack(data, field_name)
        self._check_command_injection(data, field_name)
        self._check_path_traversal(data, field_name)
    
    def _check_sql_injection(self, data: str, field_name: str) -> None:
        """Check for SQL injection patterns."""
        if self.sql_regex.search(data):
            logger.error(f"SQL injection attempt detected in {field_name}: {data[:100]}")
            raise NetraSecurityException(
                message=f"SQL injection attempt detected in {field_name}"
            )
    
    def _check_xss_attack(self, data: str, field_name: str) -> None:
        """Check for XSS attack patterns."""
        if self.xss_regex.search(data):
            logger.error(f"XSS attempt detected in {field_name}: {data[:100]}")
            raise NetraSecurityException(
                message=f"XSS attempt detected in {field_name}"
            )
    
    def _check_command_injection(self, data: str, field_name: str) -> None:
        """Check for command injection patterns."""
        if self.command_regex.search(data):
            logger.error(f"Command injection attempt detected in {field_name}: {data[:100]}")
            raise NetraSecurityException(
                message=f"Command injection attempt detected in {field_name}"
            )
    
    def _check_path_traversal(self, data: str, field_name: str) -> None:
        """Check for path traversal patterns."""
        if self.path_regex.search(data):
            logger.error(f"Path traversal attempt detected in {field_name}: {data[:100]}")
            raise NetraSecurityException(
                message=f"Path traversal attempt detected in {field_name}"
            )
    
    def sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize HTTP headers."""
        sanitized = {}
        allowed_headers = self._get_allowed_headers()
        
        for key, value in headers.items():
            if self._is_header_allowed(key, value, allowed_headers):
                sanitized[key] = value[:SecurityConfig.MAX_HEADER_SIZE]
        
        return sanitized
    
    def _get_allowed_headers(self) -> set:
        """Get set of allowed headers."""
        return {
            'content-type', 'authorization', 'user-agent', 'accept',
            'accept-encoding', 'accept-language', 'cache-control',
            'connection', 'host', 'origin', 'referer', 'x-request-id',
            'x-trace-id', 'x-forwarded-for', 'x-real-ip'
        }
    
    def _is_header_allowed(self, key: str, value: str, allowed_headers: set) -> bool:
        """Check if header is allowed."""
        return key.lower() in allowed_headers and len(value) <= SecurityConfig.MAX_HEADER_SIZE


class SecurityMiddleware(BaseHTTPMiddleware):
    """Comprehensive security middleware."""
    
    def __init__(self, app, rate_limiter: Optional[RateLimitTracker] = None):
        super().__init__(app)
        self.rate_limiter = rate_limiter or RateLimitTracker()
        self.input_validator = InputValidator()
        self.security_bearer = HTTPBearer(auto_error=False)
        
        # Sensitive endpoints requiring stricter limits
        self.sensitive_endpoints = {
            "/api/auth/login", "/api/auth/logout", "/api/auth/token",
            "/api/auth/callback", "/api/auth/refresh",
            "/api/admin", "/api/tools", "/api/synthetic-data",
            "/api/users/create", "/api/users/password"
        }
        
        # SECURITY FIX: Enhanced tracking for authentication attempts
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
            logger.error(f"Security middleware error: {e}")
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
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > SecurityConfig.MAX_REQUEST_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Request too large"
            )
    
    def _validate_url(self, request: Request) -> None:
        """Validate URL length and characters."""
        url_str = str(request.url)
        if len(url_str) > SecurityConfig.MAX_URL_LENGTH:
            raise HTTPException(
                status_code=status.HTTP_414_REQUEST_URI_TOO_LONG,
                detail="URL too long"
            )
        
        # Check for suspicious URL patterns
        if re.search(r'[<>"\'\x00-\x1f]', url_str):
            logger.warning(f"Suspicious URL characters: {url_str}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid URL characters"
            )
    
    def _validate_headers(self, request: Request) -> None:
        """Validate HTTP headers."""
        # Check for oversized headers
        for name, value in request.headers.items():
            if len(value) > SecurityConfig.MAX_HEADER_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Header {name} too large"
                )
    
    async def _check_rate_limits(self, request: Request) -> None:
        """Check rate limits."""
        client_ip = self._get_client_ip(request)
        user_id = await self._get_user_id(request)
        limit = self._determine_rate_limit(request)
        
        await self._check_ip_rate_limit(client_ip, limit)
        if user_id:
            await self._check_user_rate_limit(user_id, limit)
    
    def _determine_rate_limit(self, request: Request) -> int:
        """Determine rate limit based on endpoint sensitivity."""
        return SecurityConfig.STRICT_RATE_LIMIT if any(
            endpoint in str(request.url.path) for endpoint in self.sensitive_endpoints
        ) else SecurityConfig.DEFAULT_RATE_LIMIT
    
    async def _check_ip_rate_limit(self, client_ip: str, limit: int) -> None:
        """Check IP-based rate limit."""
        identifier = f"ip:{client_ip}"
        if self.rate_limiter.is_rate_limited(identifier, limit):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": "300"}
            )
    
    async def _check_user_rate_limit(self, user_id: str, limit: int) -> None:
        """Check user-based rate limit."""
        user_identifier = f"user:{user_id}"
        if self.rate_limiter.is_rate_limited(user_identifier, limit * 2):
            logger.warning(f"Rate limit exceeded for user: {user_id}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded for user",
                headers={"Retry-After": "300"}
            )
    
    async def _validate_request_body(self, request: Request) -> None:
        """Validate request body content."""
        try:
            body = await request.body()
            if body:
                body_str = self._decode_request_body(body)
                self.input_validator.validate_input(body_str, "request_body")
        except UnicodeDecodeError:
            self._handle_encoding_error()
    
    def _decode_request_body(self, body: bytes) -> str:
        """Decode request body to string."""
        return body.decode('utf-8', errors='ignore')
    
    def _handle_encoding_error(self) -> None:
        """Handle request body encoding errors."""
        logger.warning("Request body contains invalid UTF-8")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request encoding"
        )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded_headers = self._get_forwarded_headers()
        
        for header in forwarded_headers:
            ip = self._extract_ip_from_header(request, header)
            if ip and self._is_valid_ip(ip):
                return ip
        
        return request.client.host if request.client else "unknown"
    
    def _get_forwarded_headers(self) -> list:
        """Get list of trusted forwarded headers."""
        return [
            "x-forwarded-for",
            "x-real-ip", 
            "x-client-ip",
            "cf-connecting-ip"
        ]
    
    def _extract_ip_from_header(self, request: Request, header: str) -> Optional[str]:
        """Extract IP from forwarded header."""
        if header in request.headers:
            return request.headers[header].split(',')[0].strip()
        return None
    
    async def _get_user_id(self, request: Request) -> Optional[str]:
        """Extract user ID from request if authenticated."""
        try:
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                # This would need to be integrated with your auth system
                # For now, return None to avoid dependency issues
                return None
        except Exception:
            pass
        return None
    
    def _is_valid_ip(self, ip: str) -> bool:
        """Validate IP address format."""
        import ipaddress
        try:
            ipaddress.ip_address(ip)
            return True
        except ValueError:
            return False
    
    def _add_security_headers(self, response: Response) -> None:
        """Add security headers to response."""
        for header, value in SecurityConfig.SECURITY_HEADERS.items():
            response.headers[header] = value
        
        # Add custom security headers
        response.headers["X-Security-Middleware"] = "enabled"
        response.headers["X-Request-ID"] = f"req_{int(time.time())}"
    
    def track_auth_attempt(self, ip_address: str, success: bool) -> None:
        """Track authentication attempts for enhanced security."""
        current_time = time.time()
        
        # Track all attempts
        if ip_address not in self.auth_attempt_tracker:
            self.auth_attempt_tracker[ip_address] = []
        
        # Clean old attempts (older than 1 hour)
        self.auth_attempt_tracker[ip_address] = [
            attempt_time for attempt_time in self.auth_attempt_tracker[ip_address]
            if current_time - attempt_time < 3600
        ]
        
        self.auth_attempt_tracker[ip_address].append(current_time)
        
        # Track failed attempts specifically
        if not success:
            self.failed_auth_ips[ip_address] = self.failed_auth_ips.get(ip_address, 0) + 1
            
            # Auto-block IPs with too many failed attempts
            if self.failed_auth_ips[ip_address] >= 10:  # 10 failed attempts
                logger.error(f"IP {ip_address} blocked due to {self.failed_auth_ips[ip_address]} failed auth attempts")
                # In production, this would integrate with firewall/WAF
        else:
            # Reset failed count on successful auth
            self.failed_auth_ips[ip_address] = 0
    
    def is_ip_suspicious(self, ip_address: str) -> bool:
        """Check if IP should be treated as suspicious."""
        failed_count = self.failed_auth_ips.get(ip_address, 0)
        recent_attempts = len(self.auth_attempt_tracker.get(ip_address, []))
        
        return failed_count >= 5 or recent_attempts >= 20  # Suspicious thresholds


def create_security_middleware(rate_limiter: Optional[RateLimitTracker] = None) -> SecurityMiddleware:
    """Factory function to create security middleware."""
    return SecurityMiddleware(None, rate_limiter)


# Global rate limiter instance
global_rate_limiter = RateLimitTracker()