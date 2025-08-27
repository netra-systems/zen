"""
Core security headers middleware implementation.
Applies comprehensive security headers to HTTP responses.
"""

import hashlib
import time
from typing import Any, Callable, Dict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from netra_backend.app.logging_config import central_logger
from netra_backend.app.middleware.nonce_generator import NonceGenerator
from netra_backend.app.middleware.security_headers_config import SecurityHeadersConfig

logger = central_logger.get_logger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add comprehensive security headers."""
    
    def __init__(self, app: ASGIApp, environment: str = "development"):
        super().__init__(app)
        self.environment = environment
        self.base_headers = SecurityHeadersConfig.get_headers(environment)
        self.nonce_generator = NonceGenerator()
        self.metrics = self._initialize_metrics()
        self._log_initialization()
    
    def _initialize_metrics(self) -> Dict[str, int]:
        """Initialize security metrics tracking."""
        return {
            "requests_processed": 0,
            "csp_violations": 0,
            "security_headers_added": 0,
            "nonces_generated": 0
        }
    
    def _log_initialization(self) -> None:
        """Log middleware initialization."""
        logger.info(f"Security headers middleware initialized for {self.environment} environment")
    
    def _is_websocket_upgrade(self, request: Request) -> bool:
        """Check if request is a WebSocket upgrade request.
        
        WebSocket upgrades are identified by:
        - Upgrade: websocket header
        - Connection header containing 'upgrade'
        
        Args:
            request: The incoming request
            
        Returns:
            True if this is a WebSocket upgrade request
        """
        upgrade_header = request.headers.get("upgrade", "").lower()
        connection_header = request.headers.get("connection", "").lower()
        
        is_websocket_upgrade = (
            upgrade_header == "websocket" and 
            "upgrade" in connection_header
        )
        
        return is_websocket_upgrade
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add security headers to all responses."""
        # CRITICAL: Skip security headers for WebSocket upgrades
        # Security headers can interfere with the WebSocket upgrade process
        if self._is_websocket_upgrade(request):
            logger.debug(f"Skipping security headers for WebSocket upgrade: {request.url.path}")
            return await call_next(request)
        
        start_time = time.time()
        nonce = self.nonce_generator.generate_nonce()
        request.state.csp_nonce = nonce
        response = await call_next(request)
        return self._process_response_headers(request, response, nonce, start_time)
    
    def _process_response_headers(self, request: Request, response: Response, nonce: str, start_time: float) -> Response:
        """Process and add all security headers to response."""
        self._add_all_headers(request, response, nonce)
        self._finalize_response_processing(request, nonce, start_time)
        return response
    
    def _add_all_headers(self, request: Request, response: Response, nonce: str) -> None:
        """Add all security headers to response."""
        # Check if this is a documentation endpoint
        is_docs_endpoint = request.url.path in ["/docs", "/redoc", "/openapi.json"]
        
        if not is_docs_endpoint:
            # Only add base headers (including CSP) for non-documentation endpoints
            self._add_base_headers(response)
        else:
            # For documentation endpoints, add base headers except CSP
            self._add_base_headers_except_csp(response)
        
        self._add_dynamic_headers(request, response, nonce)
        self._add_path_specific_headers(request, response)
    
    def _finalize_response_processing(self, request: Request, nonce: str, start_time: float) -> None:
        """Finalize response processing with metrics and logging."""
        self._update_metrics(nonce)
        self._log_header_processing(request, start_time)
    
    def _add_base_headers(self, response: Response) -> None:
        """Add base security headers to response."""
        for header, value in self.base_headers.items():
            if header not in response.headers:
                response.headers[header] = value
    
    def _add_base_headers_except_csp(self, response: Response) -> None:
        """Add base security headers except CSP (for documentation endpoints)."""
        for header, value in self.base_headers.items():
            if header != "Content-Security-Policy" and header not in response.headers:
                response.headers[header] = value
    
    def _add_dynamic_headers(self, request: Request, response: Response, nonce: str) -> None:
        """Add dynamic security headers based on request/response context."""
        self._add_csp_nonce(response, nonce)
        self._add_timing_headers(response)
        self._add_request_id_header(request, response)
        self._add_environment_header(response)
        self._add_security_fingerprint(request, response)
    
    def _add_csp_nonce(self, response: Response, nonce: str) -> None:
        """Add nonce to CSP if present."""
        if "Content-Security-Policy" in response.headers and nonce:
            csp = response.headers["Content-Security-Policy"]
            updated_csp = self.nonce_generator.add_nonce_to_csp(csp, nonce)
            response.headers["Content-Security-Policy"] = updated_csp
    
    def _add_timing_headers(self, response: Response) -> None:
        """Add timing-based headers."""
        response.headers["X-Request-Start"] = str(int(time.time() * 1000))
    
    def _add_request_id_header(self, request: Request, response: Response) -> None:
        """Add request ID header if available."""
        if hasattr(request.state, "request_id") and request.state.request_id is not None:
            response.headers["X-Request-ID"] = str(request.state.request_id)
    
    def _add_environment_header(self, response: Response) -> None:
        """Add environment indicator for non-production."""
        if self.environment != "production":
            response.headers["X-Environment"] = self.environment
    
    def _add_security_fingerprint(self, request: Request, response: Response) -> None:
        """Add security fingerprint header."""
        fingerprint = self._generate_security_fingerprint(request)
        response.headers["X-Security-Fingerprint"] = fingerprint
    
    def _add_path_specific_headers(self, request: Request, response: Response) -> None:
        """Add path-specific headers."""
        if request.url.path in ["/docs", "/redoc", "/openapi.json"]:
            self._add_documentation_headers(response)
        elif request.url.path.startswith("/api/"):
            self._add_api_headers(response)
        if request.url.path.startswith("/ws"):
            self._add_websocket_headers(response)
    
    def _add_api_headers(self, response: Response) -> None:
        """Add API-specific security headers."""
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, private"
        response.headers["Expires"] = "0"
        response.headers["X-API-Version"] = "1.0"
        self._add_rate_limit_headers(response)
    
    def _add_rate_limit_headers(self, response: Response) -> None:
        """Add rate limiting headers if not present."""
        if "X-RateLimit-Remaining" not in response.headers:
            response.headers["X-RateLimit-Limit"] = "100"
            response.headers["X-RateLimit-Remaining"] = "99"
            response.headers["X-RateLimit-Reset"] = str(int(time.time()) + 3600)
    
    def _add_websocket_headers(self, response: Response) -> None:
        """Add WebSocket-specific security headers."""
        if self.environment == "production":
            response.headers["Upgrade-Insecure-Requests"] = "1"
        response.headers["X-WebSocket-Policy"] = "authenticated-only"
    
    def _add_documentation_headers(self, response: Response) -> None:
        """Add relaxed CSP headers for documentation endpoints (/docs, /redoc)."""
        # Override CSP for documentation pages to allow inline scripts and styles
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
            "font-src 'self' data: https://cdn.jsdelivr.net; "
            "img-src 'self' data: https://cdn.jsdelivr.net https://fastapi.tiangolo.com; "
            "connect-src 'self'"
        )
        response.headers["X-Frame-Options"] = "SAMEORIGIN"  # Allow embedding in same origin for docs
    
    # CORS headers removed - handled by WebSocketAwareCORSMiddleware in middleware_setup.py
    # This was legacy code that violated SSOT principles
    
    def _generate_security_fingerprint(self, request: Request) -> str:
        """Generate a security fingerprint for the request."""
        client_host = request.client.host if request.client else 'unknown'
        fingerprint_data = f"{request.method}:{request.url.path}:{client_host}:{time.time()}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
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
                **self.metrics,
                "environment": self.environment
            },
            "headers_config": self._get_headers_config()
        }
    
    def _get_headers_config(self) -> Dict[str, Any]:
        """Get headers configuration status."""
        return {
            "total_headers": len(self.base_headers),
            "csp_enabled": "Content-Security-Policy" in self.base_headers,
            "hsts_enabled": "Strict-Transport-Security" in self.base_headers,
            "frame_protection": "X-Frame-Options" in self.base_headers
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of security headers."""
        metrics_data = self._calculate_health_metrics()
        status = self._determine_health_status(metrics_data["health_score"])
        return self._build_health_status_response(metrics_data, status)
    
    def _calculate_health_metrics(self) -> Dict[str, float]:
        """Calculate health metrics from request data."""
        total_requests = self.metrics["requests_processed"]
        violation_rate = self.metrics["csp_violations"] / max(1, total_requests)
        health_score = max(0.0, 1.0 - (violation_rate * 2))
        return self._build_health_metrics_dict(health_score, violation_rate, total_requests)
    
    def _build_health_metrics_dict(self, health_score: float, violation_rate: float, total_requests: int) -> Dict[str, float]:
        """Build health metrics dictionary."""
        return {
            "health_score": health_score,
            "violation_rate": violation_rate,
            "total_requests": total_requests
        }
    
    def _build_health_status_response(self, metrics_data: Dict[str, float], status: str) -> Dict[str, Any]:
        """Build complete health status response."""
        base_response = self._build_base_health_response(metrics_data, status)
        base_response["security_features"] = self._get_security_features_status()
        return base_response
    
    def _build_base_health_response(self, metrics_data: Dict[str, float], status: str) -> Dict[str, Any]:
        """Build base health response without security features."""
        return {
            "status": status,
            "health_score": metrics_data["health_score"],
            "violation_rate": metrics_data["violation_rate"],
            "total_requests": metrics_data["total_requests"]
        }
    
    def _determine_health_status(self, health_score: float) -> str:
        """Determine health status based on score."""
        if health_score < 0.5:
            return "unhealthy"
        elif health_score < 0.8:
            return "degraded"
        return "healthy"
    
    def _get_security_features_status(self) -> Dict[str, bool]:
        """Get security features status."""
        return {
            "csp_active": "Content-Security-Policy" in self.base_headers,
            "hsts_active": "Strict-Transport-Security" in self.base_headers,
            "xss_protection": "X-XSS-Protection" in self.base_headers,
            "frame_protection": "X-Frame-Options" in self.base_headers
        }