"""
Security headers middleware for comprehensive protection.
Implements security headers following OWASP recommendations and industry best practices.
"""

from typing import Dict, Optional, Callable, Any
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import hashlib
import secrets
from datetime import datetime

from app.logging_config import central_logger
from app.config import settings

logger = central_logger.get_logger(__name__)


class SecurityHeadersConfig:
    """Configuration for security headers based on environment."""
    
    @staticmethod
    def get_headers(environment: str = "development") -> Dict[str, str]:
        """Get security headers based on environment."""
        
        base_headers = {
            # Prevent MIME type sniffing
            "X-Content-Type-Options": "nosniff",
            
            # Prevent clickjacking
            "X-Frame-Options": "DENY",
            
            # XSS protection
            "X-XSS-Protection": "1; mode=block",
            
            # Referrer policy
            "Referrer-Policy": "strict-origin-when-cross-origin",
            
            # Disable feature policy for sensitive features
            "Permissions-Policy": SecurityHeadersConfig._get_permissions_policy(),
            
            # Security headers for API responses
            "X-Robots-Tag": "noindex, nofollow, noarchive, nosnippet",
            
            # Cache control for sensitive endpoints
            "Cache-Control": "no-store, no-cache, must-revalidate, private",
            "Pragma": "no-cache",
            "Expires": "0",
        }
        
        if environment == "production":
            base_headers.update({
                # Strict Transport Security for production
                "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
                
                # Production CSP
                "Content-Security-Policy": SecurityHeadersConfig._get_production_csp(),
                
                # HPKP (Public Key Pinning) - be very careful with this
                # "Public-Key-Pins": "pin-sha256=\"base64+primary==\"; pin-sha256=\"base64+backup==\"; max-age=5184000; includeSubDomains",
            })
        elif environment == "staging":
            base_headers.update({
                # Less strict HSTS for staging
                "Strict-Transport-Security": "max-age=86400; includeSubDomains",
                
                # Staging CSP
                "Content-Security-Policy": SecurityHeadersConfig._get_staging_csp(),
            })
        else:  # development
            base_headers.update({
                # Development CSP - more permissive
                "Content-Security-Policy": SecurityHeadersConfig._get_development_csp(),
            })
        
        return base_headers
    
    @staticmethod
    def _get_permissions_policy() -> str:
        """Get permissions policy directive."""
        # Disable sensitive features by default
        disabled_features = [
            "geolocation=()",
            "microphone=()",
            "camera=()",
            "payment=()",
            "usb=()",
            "magnetometer=()",
            "gyroscope=()",
            "accelerometer=()",
            "ambient-light-sensor=()",
            "autoplay=()",
            "encrypted-media=()",
            "fullscreen=()",
            "picture-in-picture=()"
        ]
        return ", ".join(disabled_features)
    
    @staticmethod
    def _get_production_csp() -> str:
        """Get production Content Security Policy."""
        # Very strict CSP for production
        directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' https://apis.google.com",
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
            "font-src 'self' https://fonts.gstatic.com",
            "img-src 'self' data: https:",
            "connect-src 'self' https://api.netrasystems.ai wss://api.netrasystems.ai",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'",
            "upgrade-insecure-requests"
        ]
        return "; ".join(directives)
    
    @staticmethod
    def _get_staging_csp() -> str:
        """Get staging Content Security Policy."""
        # Moderately strict CSP for staging
        directives = [
            "default-src 'self'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https:",
            "style-src 'self' 'unsafe-inline' https:",
            "font-src 'self' https: data:",
            "img-src 'self' data: https:",
            "connect-src 'self' https: wss:",
            "frame-ancestors 'none'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        return "; ".join(directives)
    
    @staticmethod
    def _get_development_csp() -> str:
        """Get development Content Security Policy."""
        # Permissive CSP for development
        directives = [
            "default-src 'self' 'unsafe-inline' 'unsafe-eval'",
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' http: https:",
            "style-src 'self' 'unsafe-inline' http: https:",
            "font-src 'self' http: https: data:",
            "img-src 'self' data: http: https:",
            "connect-src 'self' http: https: ws: wss:",
            "frame-ancestors 'self'",
            "base-uri 'self'",
            "form-action 'self'"
        ]
        return "; ".join(directives)


class NonceGenerator:
    """Generate cryptographic nonces for CSP."""
    
    @staticmethod
    def generate_nonce() -> str:
        """Generate a cryptographically secure nonce."""
        return secrets.token_urlsafe(16)
    
    @staticmethod
    def add_nonce_to_csp(csp: str, nonce: str) -> str:
        """Add nonce to CSP script-src directive."""
        nonce_directive = f"'nonce-{nonce}'"
        
        # Add nonce to script-src
        if "script-src" in csp:
            csp = csp.replace("script-src", f"script-src {nonce_directive}")
        else:
            csp += f"; script-src 'self' {nonce_directive}"
        
        # Add nonce to style-src
        if "style-src" in csp:
            csp = csp.replace("style-src", f"style-src {nonce_directive}")
        else:
            csp += f"; style-src 'self' {nonce_directive}"
        
        return csp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add comprehensive security headers."""
    
    def __init__(self, app: ASGIApp, environment: str = "development"):
        super().__init__(app)
        self.environment = environment
        self.base_headers = SecurityHeadersConfig.get_headers(environment)
        self.nonce_generator = NonceGenerator()
        
        # Track security metrics
        self.metrics = {
            "requests_processed": 0,
            "csp_violations": 0,
            "security_headers_added": 0,
            "nonces_generated": 0
        }
        
        logger.info(f"Security headers middleware initialized for {environment} environment")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to all responses."""
        start_time = time.time()
        nonce = self.nonce_generator.generate_nonce()
        request.state.csp_nonce = nonce
        
        response = await call_next(request)
        return self._process_response_headers(request, response, nonce, start_time)
    
    def _process_response_headers(self, request: Request, response: Response, nonce: str, start_time: float) -> Response:
        """Process and add all security headers to response."""
        self._add_base_headers(response)
        self._add_dynamic_headers(request, response, nonce)
        self._add_path_specific_headers(request, response)
        self._update_metrics(nonce)
        self._log_header_processing(request, start_time)
        return response
    
    def _add_path_specific_headers(self, request: Request, response: Response) -> None:
        """Add path-specific headers."""
        if request.url.path.startswith("/api/"):
            self._add_api_headers(response)
        if request.url.path.startswith("/ws"):
            self._add_websocket_headers(response)
    
    def _update_metrics(self, nonce: str) -> None:
        """Update middleware metrics."""
        self.metrics["requests_processed"] += 1
        self.metrics["security_headers_added"] += 1
        if nonce:
            self.metrics["nonces_generated"] += 1
    
    def _log_header_processing(self, request: Request, start_time: float) -> None:
        """Log security header processing time."""
        processing_time = time.time() - start_time
        logger.debug(f"Applied security headers to {request.method} {request.url.path} in {processing_time:.3f}s")
    
    def _add_base_headers(self, response: Response) -> None:
        """Add base security headers to response."""
        for header, value in self.base_headers.items():
            if header not in response.headers:
                response.headers[header] = value
    
    def _add_dynamic_headers(self, request: Request, response: Response, nonce: str) -> None:
        """Add dynamic security headers based on request/response context."""
        
        # Add nonce to CSP if CSP is present
        if "Content-Security-Policy" in response.headers and nonce:
            csp = response.headers["Content-Security-Policy"]
            updated_csp = self.nonce_generator.add_nonce_to_csp(csp, nonce)
            response.headers["Content-Security-Policy"] = updated_csp
        
        # Add timing-based headers
        response.headers["X-Request-Start"] = str(int(time.time() * 1000))
        
        # Add request ID if available
        if hasattr(request.state, "request_id") and request.state.request_id is not None:
            response.headers["X-Request-ID"] = str(request.state.request_id)
        
        # Add environment indicator (for non-production)
        if self.environment != "production":
            response.headers["X-Environment"] = self.environment
        
        # Add security fingerprint
        security_fingerprint = self._generate_security_fingerprint(request)
        response.headers["X-Security-Fingerprint"] = security_fingerprint
    
    def _add_api_headers(self, response: Response) -> None:
        """Add API-specific security headers."""
        # Ensure no caching for API responses
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Expires"] = "0"
        
        # API versioning
        response.headers["X-API-Version"] = "1.0"
        
        # Rate limiting headers (if rate limiting is active)
        # These would be populated by rate limiting middleware
        if "X-RateLimit-Remaining" not in response.headers:
            response.headers["X-RateLimit-Limit"] = "100"
            response.headers["X-RateLimit-Remaining"] = "99"
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 3600)
    
    def _add_websocket_headers(self, response: Response) -> None:
        """Add WebSocket-specific security headers."""
        # WebSocket connections should be secure
        if self.environment == "production":
            response.headers["Upgrade-Insecure-Requests"] = "1"
        
        # Add WebSocket security policy
        response.headers["X-WebSocket-Policy"] = "authenticated-only"
    
    def _generate_security_fingerprint(self, request: Request) -> str:
        """Generate a security fingerprint for the request."""
        # Create a fingerprint based on request characteristics
        fingerprint_data = f"{request.method}:{request.url.path}:{request.client.host if request.client else 'unknown'}:{time.time()}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    def handle_csp_violation(self, violation_report: Dict[str, Any]) -> None:
        """Handle CSP violation reports."""
        self.metrics["csp_violations"] += 1
        logger.warning(f"CSP Violation: {violation_report}")
        self._log_violation_details(violation_report)
    
    def _log_violation_details(self, violation_report: Dict[str, Any]) -> None:
        """Log detailed CSP violation information."""
        blocked_uri = violation_report.get("blocked-uri", "unknown")
        violated_directive = violation_report.get("violated-directive", "unknown")
        source_file = violation_report.get("source-file", "unknown")
        logger.error(f"CSP Violation - Directive: {violated_directive}, URI: {blocked_uri}, Source: {source_file}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get security headers metrics."""
        return {
            "security_headers": {
                "requests_processed": self.metrics["requests_processed"],
                "security_headers_added": self.metrics["security_headers_added"],
                "nonces_generated": self.metrics["nonces_generated"],
                "csp_violations": self.metrics["csp_violations"],
                "environment": self.environment
            },
            "headers_config": {
                "total_headers": len(self.base_headers),
                "csp_enabled": "Content-Security-Policy" in self.base_headers,
                "hsts_enabled": "Strict-Transport-Security" in self.base_headers,
                "frame_protection": "X-Frame-Options" in self.base_headers
            }
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of security headers."""
        total_requests = self.metrics["requests_processed"]
        violation_rate = self.metrics["csp_violations"] / max(1, total_requests)
        
        health_score = max(0.0, 1.0 - (violation_rate * 2))  # Violations reduce health score
        
        status = "healthy"
        if health_score < 0.5:
            status = "unhealthy"
        elif health_score < 0.8:
            status = "degraded"
        
        return {
            "status": status,
            "health_score": health_score,
            "violation_rate": violation_rate,
            "total_requests": total_requests,
            "security_features": {
                "csp_active": "Content-Security-Policy" in self.base_headers,
                "hsts_active": "Strict-Transport-Security" in self.base_headers,
                "xss_protection": "X-XSS-Protection" in self.base_headers,
                "frame_protection": "X-Frame-Options" in self.base_headers
            }
        }


def create_security_headers_middleware(environment: Optional[str] = None) -> SecurityHeadersMiddleware:
    """Factory function to create security headers middleware."""
    if not environment:
        environment = getattr(settings, 'environment', 'development')
    
    return SecurityHeadersMiddleware(None, environment)


# CSP violation reporting endpoint handler
async def handle_csp_violation_report(request: Request, middleware: SecurityHeadersMiddleware):
    """Handle CSP violation reports."""
    try:
        violation_data = await request.json()
        middleware.handle_csp_violation(violation_data.get("csp-report", {}))
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Error handling CSP violation report: {e}")
        return {"status": "error", "message": str(e)}


# Global instance (to be initialized by app factory)
security_headers_middleware = None