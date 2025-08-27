"""
CORS Monitoring Middleware

Business Value Justification (BVJ):
- Segment: ALL (Required for operational visibility)
- Business Goal: Monitor CORS performance and security
- Value Impact: Prevents CORS-related outages through proactive monitoring
- Strategic Impact: Enables data-driven CORS policy decisions

This middleware collects metrics and logs for CORS requests to enable:
- Performance monitoring
- Security analysis
- Policy optimization
- Incident response
"""

import logging
import time
from typing import Callable, Dict, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from prometheus_client import Counter, Histogram, Gauge

from shared.cors_config_builder import CORSConfigurationBuilder

logger = logging.getLogger(__name__)

# Prometheus metrics for CORS monitoring
cors_requests_total = Counter(
    'cors_requests_total',
    'Total number of CORS requests',
    ['method', 'origin_type', 'status_code', 'service']
)

cors_preflight_requests_total = Counter(
    'cors_preflight_requests_total', 
    'Total number of CORS preflight requests',
    ['origin_type', 'allowed', 'service']
)

cors_request_duration = Histogram(
    'cors_request_duration_seconds',
    'Duration of CORS requests',
    ['method', 'origin_type', 'service'],
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
)

cors_origin_attempts = Counter(
    'cors_origin_attempts_total',
    'Attempts by specific origins (aggregated)',
    ['origin_hash', 'allowed', 'service']
)

cors_blocked_attempts = Counter(
    'cors_blocked_attempts_total',
    'Blocked CORS attempts by type',
    ['reason', 'service']
)

cors_policy_hits = Counter(
    'cors_policy_hits_total',
    'CORS policy evaluation hits',
    ['policy_type', 'environment', 'service']
)

cors_active_origins = Gauge(
    'cors_active_origins',
    'Number of unique origins seen recently',
    ['time_window', 'service']
)


class CORSMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor CORS requests and collect metrics.
    
    This middleware runs alongside CORS handling middleware to collect
    operational data about CORS usage patterns, performance, and security.
    """
    
    def __init__(self, app, service_name: str = "backend", environment: str = "development"):
        """Initialize CORS monitoring middleware."""
        super().__init__(app)
        self.service_name = service_name
        self.environment = environment
        
        # Initialize CORS configuration builder
        env_vars = {"ENVIRONMENT": environment} if environment else None
        self.cors = CORSConfigurationBuilder(env_vars)
        self.allowed_origins = set(self.cors.origins.allowed)
        
        # In-memory tracking for active origins (last hour)
        self.recent_origins = defaultdict(list)
        self.last_cleanup = datetime.now()
        
        logger.info(f"CORSMonitoringMiddleware initialized for {service_name} in {environment}")
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor CORS request and collect metrics."""
        start_time = time.time()
        origin = request.headers.get("origin")
        is_preflight = request.method == "OPTIONS" and origin is not None
        
        # Determine origin type for metrics
        origin_type = self._classify_origin(origin)
        
        # Track preflight requests
        if is_preflight:
            is_allowed = self._is_origin_allowed(origin)
            cors_preflight_requests_total.labels(
                origin_type=origin_type,
                allowed=str(is_allowed).lower(),
                service=self.service_name
            ).inc()
            
            if not is_allowed:
                reason = self._get_block_reason(origin)
                cors_blocked_attempts.labels(
                    reason=reason,
                    service=self.service_name
                ).inc()
        
        # Track origin attempts (with hash for privacy)
        if origin:
            origin_hash = self._hash_origin(origin)
            is_allowed = self._is_origin_allowed(origin)
            
            cors_origin_attempts.labels(
                origin_hash=origin_hash,
                allowed=str(is_allowed).lower(),
                service=self.service_name
            ).inc()
            
            # Update active origins tracking
            self._track_active_origin(origin)
        
        # Track policy evaluation
        cors_policy_hits.labels(
            policy_type=self._get_policy_type(origin),
            environment=self.environment,
            service=self.service_name
        ).inc()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate duration and record metrics
        duration = time.time() - start_time
        
        cors_requests_total.labels(
            method=request.method,
            origin_type=origin_type,
            status_code=response.status_code,
            service=self.service_name
        ).inc()
        
        cors_request_duration.labels(
            method=request.method,
            origin_type=origin_type,
            service=self.service_name
        ).observe(duration)
        
        # Log suspicious activity
        self._log_security_events(request, response, origin, duration)
        
        # Periodic cleanup and gauge updates
        self._update_gauges()
        
        return response
    
    def _classify_origin(self, origin: Optional[str]) -> str:
        """Classify origin type for metrics."""
        if not origin:
            return "no_origin"
        
        if origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
            return "localhost"
        elif origin.startswith("http://[::1]"):
            return "ipv6_localhost"
        elif "staging" in origin:
            return "staging"
        elif any(domain in origin for domain in ["netrasystems.ai"]):
            return "production"
        elif origin.startswith("https://"):
            return "external_https"
        elif origin.startswith("http://"):
            return "external_http"
        else:
            return "unknown"
    
    def _is_origin_allowed(self, origin: Optional[str]) -> bool:
        """Check if origin is allowed (cached check)."""
        if not origin:
            return False
        
        return self.cors.origins.is_allowed(origin)
    
    def _get_block_reason(self, origin: Optional[str]) -> str:
        """Get reason why origin was blocked."""
        if not origin:
            return "no_origin"
        elif origin.startswith("http://") and self.environment == "production":
            return "http_in_production"
        elif "localhost" in origin and self.environment == "production":
            return "localhost_in_production"
        elif self._is_suspicious_origin(origin):
            return "suspicious_origin"
        else:
            return "not_in_allowlist"
    
    def _is_suspicious_origin(self, origin: str) -> bool:
        """Check if origin appears suspicious."""
        suspicious_patterns = [
            "malicious", "attack", "hack", "exploit", "phishing",
            "spam", "bot", "crawler", "evil", "bad"
        ]
        
        origin_lower = origin.lower()
        return any(pattern in origin_lower for pattern in suspicious_patterns)
    
    def _get_policy_type(self, origin: Optional[str]) -> str:
        """Get the policy type that would handle this origin."""
        if not origin:
            return "no_origin_policy"
        
        if self.environment == "development":
            if "localhost" in origin or "127.0.0.1" in origin:
                return "development_localhost"
            else:
                return "development_external"
        elif self.environment == "staging":
            if "staging" in origin:
                return "staging_domain"
            elif "localhost" in origin:
                return "staging_localhost_fallback"
            else:
                return "staging_external"
        else:  # production
            if "netrasystems.ai" in origin:
                return "production_domain"
            else:
                return "production_external"
    
    def _hash_origin(self, origin: str) -> str:
        """Create a privacy-preserving hash of origin for metrics."""
        import hashlib
        
        # Hash only the domain part for privacy
        try:
            from urllib.parse import urlparse
            parsed = urlparse(origin)
            domain = parsed.netloc
            return hashlib.sha256(domain.encode()).hexdigest()[:8]
        except Exception:
            return "unknown_hash"
    
    def _track_active_origin(self, origin: str) -> None:
        """Track active origins for gauge metrics."""
        now = datetime.now()
        self.recent_origins[origin].append(now)
        
        # Clean old entries periodically
        if now - self.last_cleanup > timedelta(minutes=5):
            self._cleanup_old_origins()
            self.last_cleanup = now
    
    def _cleanup_old_origins(self) -> None:
        """Remove old origin tracking data."""
        cutoff = datetime.now() - timedelta(hours=1)
        
        for origin in list(self.recent_origins.keys()):
            # Keep only recent timestamps
            self.recent_origins[origin] = [
                ts for ts in self.recent_origins[origin] if ts > cutoff
            ]
            
            # Remove empty entries
            if not self.recent_origins[origin]:
                del self.recent_origins[origin]
    
    def _update_gauges(self) -> None:
        """Update gauge metrics."""
        # Update active origins count
        cors_active_origins.labels(
            time_window="1hour",
            service=self.service_name
        ).set(len(self.recent_origins))
    
    def _log_security_events(
        self, 
        request: Request, 
        response: Response, 
        origin: Optional[str], 
        duration: float
    ) -> None:
        """Log potential security events."""
        # Log blocked requests
        if origin and not self._is_origin_allowed(origin):
            logger.warning(
                f"CORS blocked origin: {origin} "
                f"method={request.method} "
                f"path={request.url.path} "
                f"status={response.status_code} "
                f"duration={duration:.3f}s"
            )
        
        # Log suspicious patterns
        if origin and self._is_suspicious_origin(origin):
            logger.warning(
                f"Suspicious CORS origin: {origin} "
                f"method={request.method} "
                f"path={request.url.path}"
            )
        
        # Log slow CORS requests (may indicate attacks)
        if duration > 1.0:  # > 1 second
            logger.info(
                f"Slow CORS request: origin={origin} "
                f"method={request.method} "
                f"path={request.url.path} "
                f"duration={duration:.3f}s"
            )
        
        # Log high error rates (may indicate misconfigurations)
        if response.status_code >= 400:
            logger.info(
                f"CORS error response: origin={origin} "
                f"method={request.method} "
                f"path={request.url.path} "
                f"status={response.status_code}"
            )


def get_cors_monitoring_metrics() -> Dict[str, any]:
    """
    Get current CORS monitoring metrics for health checks.
    
    Returns:
        Dictionary containing current CORS metrics
    """
    from prometheus_client import REGISTRY
    
    metrics = {}
    
    try:
        # Get metric values from registry
        for collector in REGISTRY._collector_to_names.keys():
            if hasattr(collector, '_name') and 'cors' in collector._name:
                metrics[collector._name] = {
                    'help': getattr(collector, '_documentation', ''),
                    'type': collector.__class__.__name__,
                }
                
                # Get current values for counters/gauges
                if hasattr(collector, '_value'):
                    metrics[collector._name]['value'] = collector._value
                elif hasattr(collector, '_samples'):
                    metrics[collector._name]['samples'] = len(collector._samples)
                    
    except Exception as e:
        logger.error(f"Error collecting CORS metrics: {e}")
        metrics['error'] = str(e)
    
    return metrics


def create_cors_monitoring_dashboard_config() -> Dict[str, any]:
    """
    Generate Grafana dashboard configuration for CORS monitoring.
    
    Returns:
        Grafana dashboard JSON configuration
    """
    dashboard_config = {
        "dashboard": {
            "title": "CORS Monitoring",
            "tags": ["cors", "security", "api"],
            "time": {"from": "now-1h", "to": "now"},
            "panels": [
                {
                    "title": "CORS Requests Rate",
                    "type": "graph",
                    "targets": [{
                        "expr": "rate(cors_requests_total[5m])",
                        "legendFormat": "{{method}} {{origin_type}}"
                    }]
                },
                {
                    "title": "CORS Preflight Success Rate", 
                    "type": "stat",
                    "targets": [{
                        "expr": "rate(cors_preflight_requests_total{allowed=\"true\"}[5m]) / rate(cors_preflight_requests_total[5m])",
                        "legendFormat": "Success Rate"
                    }]
                },
                {
                    "title": "Blocked Origins",
                    "type": "graph",
                    "targets": [{
                        "expr": "rate(cors_blocked_attempts_total[5m])",
                        "legendFormat": "{{reason}}"
                    }]
                },
                {
                    "title": "Request Duration",
                    "type": "heatmap",
                    "targets": [{
                        "expr": "cors_request_duration_seconds",
                        "legendFormat": "Duration"
                    }]
                },
                {
                    "title": "Active Origins",
                    "type": "stat",
                    "targets": [{
                        "expr": "cors_active_origins",
                        "legendFormat": "{{time_window}}"
                    }]
                }
            ]
        }
    }
    
    return dashboard_config