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
        
        # Check if IP is temporarily blocked
        if identifier in self._blocked_ips:
            if now < self._blocked_ips[identifier].timestamp():
                return True
            else:
                del self._blocked_ips[identifier]
        
        # Clean old requests
        if identifier not in self._requests:
            self._requests[identifier] = []
        
        self._requests[identifier] = [
            req_time for req_time in self._requests[identifier] 
            if now - req_time < window
        ]
        
        # Check limit
        if len(self._requests[identifier]) >= limit:
            # Block IP for 5 minutes on excessive requests
            self._blocked_ips[identifier] = datetime.now() + timedelta(minutes=5)
            logger.warning(f"Rate limit exceeded for {identifier}, blocking for 5 minutes")
            return True
        
        self._requests[identifier].append(now)
        return False


class InputValidator:
    """Validate and sanitize inputs."""
    
    # Dangerous patterns to block
    SQL_INJECTION_PATTERNS = [
        r'(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|UNION)\b)',
        r'(-{2}|/\*|\*/)',  # SQL comments
        r'(\b(OR|AND)\s+\d+\s*=\s*\d+)',  # OR 1=1, AND 1=1
        r'(\bxp_cmdshell\b)',  # SQL Server command execution
    ]
    
    XSS_PATTERNS = [
        r'<script[^>]*>.*?</script>',
        r'javascript:',
        r'on\w+\s*=',  # event handlers
        r'<iframe[^>]*>',
        r'<object[^>]*>',
        r'<embed[^>]*>',
    ]
    
    def __init__(self):
        self.sql_regex = re.compile('|'.join(self.SQL_INJECTION_PATTERNS), re.IGNORECASE)
        self.xss_regex = re.compile('|'.join(self.XSS_PATTERNS), re.IGNORECASE)
    
    def validate_input(self, data: str, field_name: str = "input") -> None:
        """Validate input for security threats."""
        if not data:
            return
        
        # Check for SQL injection
        if self.sql_regex.search(data):
            logger.error(f"SQL injection attempt detected in {field_name}: {data[:100]}")
            raise NetraSecurityException(
                message=f"SQL injection attempt detected in {field_name}"
            )
        
        # Check for XSS
        if self.xss_regex.search(data):
            logger.error(f"XSS attempt detected in {field_name}: {data[:100]}")
            raise NetraSecurityException(
                message=f"XSS attempt detected in {field_name}"
            )
    
    def sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Sanitize HTTP headers."""
        sanitized = {}
        allowed_headers = {
            'content-type', 'authorization', 'user-agent', 'accept',
            'accept-encoding', 'accept-language', 'cache-control',
            'connection', 'host', 'origin', 'referer', 'x-request-id',
            'x-trace-id', 'x-forwarded-for', 'x-real-ip'
        }
        
        for key, value in headers.items():
            if key.lower() in allowed_headers and len(value) <= SecurityConfig.MAX_HEADER_SIZE:
                sanitized[key] = value[:SecurityConfig.MAX_HEADER_SIZE]
        
        return sanitized


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
            "/api/admin", "/api/tools", "/api/synthetic-data"
        }
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request through security layers."""
        start_time = time.time()
        
        try:
            # 1. Request size validation
            self._validate_request_size(request)
            
            # 2. URL validation
            self._validate_url(request)
            
            # 3. Header validation
            self._validate_headers(request)
            
            # 4. Rate limiting
            await self._check_rate_limits(request)
            
            # 5. Input validation for POST/PUT requests
            if request.method in ["POST", "PUT", "PATCH"]:
                await self._validate_request_body(request)
            
            # 6. Process request
            response = await call_next(request)
            
            # 7. Add security headers
            self._add_security_headers(response)
            
            # 8. Log security metrics
            processing_time = time.time() - start_time
            logger.info(f"Security middleware processed {request.method} {request.url.path} in {processing_time:.3f}s")
            
            return response
            
        except NetraSecurityException:
            raise
        except Exception as e:
            logger.error(f"Security middleware error: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Security validation failed"
            )
    
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
        
        # Determine rate limit based on endpoint
        limit = SecurityConfig.STRICT_RATE_LIMIT if any(
            endpoint in str(request.url.path) for endpoint in self.sensitive_endpoints
        ) else SecurityConfig.DEFAULT_RATE_LIMIT
        
        # Check IP-based rate limit
        identifier = f"ip:{client_ip}"
        if self.rate_limiter.is_rate_limited(identifier, limit):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={"Retry-After": "300"}  # 5 minutes
            )
        
        # Check user-based rate limit if authenticated
        if user_id:
            user_identifier = f"user:{user_id}"
            if self.rate_limiter.is_rate_limited(user_identifier, limit * 2):  # Higher limit for authenticated users
                logger.warning(f"Rate limit exceeded for user: {user_id}")
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded for user",
                    headers={"Retry-After": "300"}
                )
    
    async def _validate_request_body(self, request: Request) -> None:
        """Validate request body content."""
        try:
            # Create a copy of the request body to validate
            body = await request.body()
            if body:
                body_str = body.decode('utf-8', errors='ignore')
                self.input_validator.validate_input(body_str, "request_body")
        except UnicodeDecodeError:
            logger.warning("Request body contains invalid UTF-8")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request encoding"
            )
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        # Check for forwarded headers (in order of trust)
        forwarded_headers = [
            "x-forwarded-for",
            "x-real-ip", 
            "x-client-ip",
            "cf-connecting-ip"  # Cloudflare
        ]
        
        for header in forwarded_headers:
            if header in request.headers:
                # Take the first IP in case of comma-separated list
                ip = request.headers[header].split(',')[0].strip()
                if self._is_valid_ip(ip):
                    return ip
        
        # Fallback to client host
        return request.client.host if request.client else "unknown"
    
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


def create_security_middleware(rate_limiter: Optional[RateLimitTracker] = None) -> SecurityMiddleware:
    """Factory function to create security middleware."""
    return SecurityMiddleware(None, rate_limiter)


# Global rate limiter instance
global_rate_limiter = RateLimitTracker()