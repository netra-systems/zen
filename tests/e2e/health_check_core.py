"""
Health Check Core Types and Constants

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Operational reliability foundation
- Value Impact: Enables $15K MRR health monitoring system
- Revenue Impact: Prevents service outage costs

Core components for multi-service health checking:
- HealthCheckResult data structure
- Service endpoint configurations  
- Database timeout constants
- Common health checking utilities

CRITICAL: Maximum 300 lines, modular design for reusability
"""

import os
from datetime import UTC, datetime
from typing import Any, Dict, Optional

# Set testing environment before any imports
os.environ["TESTING"] = "1"
os.environ["ENVIRONMENT"] = "testing"
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"


class HealthCheckResult:
    """Structured health check result with timing and error details."""
    
    def __init__(self, service: str, status: str, response_time_ms: float, 
                 details: Optional[Dict[str, Any]] = None, error: Optional[str] = None):
        self.service = service
        self.status = status
        self.response_time_ms = response_time_ms
        self.details = details or {}
        self.error = error
        self.timestamp = datetime.now(UTC)
    
    def is_healthy(self) -> bool:
        """Check if service is in healthy state."""
        return self.status == "healthy"
    
    def is_available(self) -> bool:
        """Check if service is available (healthy or degraded).""" 
        return self.status in ["healthy", "degraded", "disabled"]
    
    def __repr__(self) -> str:
        """String representation for debugging."""
        return f"HealthCheckResult(service={self.service}, status={self.status}, time={self.response_time_ms:.1f}ms)"


# Service endpoints and timeout configurations
SERVICE_ENDPOINTS = {
    "auth": {
        "url": "http://localhost:8081/health",
        "timeout": 5.0,
        "expected_service": "auth-service",
        "critical": True
    },
    "backend": {
        "url": "http://localhost:8000/health", 
        "timeout": 5.0,
        "expected_service": "netra_backend",
        "critical": True
    },
    "frontend": {
        "url": "http://localhost:3000",
        "timeout": 10.0,
        "check_type": "build_verification",
        "critical": False
    }
}

DATABASE_TIMEOUTS = {
    "postgres": 3.0,
    "clickhouse": 5.0, 
    "redis": 2.0
}

# Health status constants
HEALTH_STATUS = {
    "HEALTHY": "healthy",
    "UNHEALTHY": "unhealthy", 
    "TIMEOUT": "timeout",
    "ERROR": "error",
    "DISABLED": "disabled",
    "SKIPPED": "skipped"
}

# Response time thresholds (milliseconds)
RESPONSE_TIME_THRESHOLDS = {
    "excellent": 100,
    "good": 500,
    "acceptable": 2000,
    "poor": 5000
}


def get_response_time_rating(response_time_ms: float) -> str:
    """Get performance rating based on response time."""
    if response_time_ms <= RESPONSE_TIME_THRESHOLDS["excellent"]:
        return "excellent"
    elif response_time_ms <= RESPONSE_TIME_THRESHOLDS["good"]:
        return "good"
    elif response_time_ms <= RESPONSE_TIME_THRESHOLDS["acceptable"]:
        return "acceptable"
    elif response_time_ms <= RESPONSE_TIME_THRESHOLDS["poor"]:
        return "poor"
    else:
        return "critical"


def create_service_error_result(service: str, error: str, response_time_ms: float = 0) -> HealthCheckResult:
    """Create standardized error result for service health check."""
    return HealthCheckResult(
        service=service,
        status=HEALTH_STATUS["ERROR"],
        response_time_ms=response_time_ms,
        error=error
    )


def create_timeout_result(service: str, timeout_ms: float) -> HealthCheckResult:
    """Create standardized timeout result for service health check."""
    return HealthCheckResult(
        service=service,
        status=HEALTH_STATUS["TIMEOUT"],
        response_time_ms=timeout_ms,
        error="Request timeout"
    )


def create_healthy_result(service: str, response_time_ms: float, details: Optional[Dict[str, Any]] = None) -> HealthCheckResult:
    """Create standardized healthy result for service health check."""
    return HealthCheckResult(
        service=service,
        status=HEALTH_STATUS["HEALTHY"],
        response_time_ms=response_time_ms,
        details=details or {}
    )


def create_disabled_result(service: str, reason: str) -> HealthCheckResult:
    """Create standardized disabled result for service health check."""
    return HealthCheckResult(
        service=service,
        status=HEALTH_STATUS["DISABLED"],
        response_time_ms=0,
        details={"reason": reason}
    )


def validate_service_response(response_data: Dict[str, Any], expected_service: Optional[str]) -> bool:
    """Validate service response matches expected service identifier."""
    if not expected_service:
        return True
    
    actual_service = response_data.get("service")
    return actual_service == expected_service


def get_critical_services() -> list[str]:
    """Get list of services marked as critical for system operation."""
    return [name for name, config in SERVICE_ENDPOINTS.items() if config.get("critical", False)]


def calculate_overall_health_score(results: list[HealthCheckResult]) -> float:
    """Calculate overall system health score (0.0 to 1.0)."""
    if not results:
        return 0.0
    
    healthy_count = sum(1 for r in results if r.is_healthy())
    available_count = sum(1 for r in results if r.is_available())
    
    # Weight healthy services higher than just available
    health_score = (healthy_count * 1.0 + (available_count - healthy_count) * 0.5) / len(results)
    return min(1.0, max(0.0, health_score))


def format_health_summary(results: list[HealthCheckResult]) -> str:
    """Format health check results into human-readable summary."""
    if not results:
        return "No health check results"
    
    healthy_count = sum(1 for r in results if r.is_healthy())
    total_count = len(results)
    health_score = calculate_overall_health_score(results)
    
    summary_lines = [
        f"Health Summary: {healthy_count}/{total_count} services healthy",
        f"Overall Score: {health_score:.2f}",
        ""
    ]
    
    for result in results:
        status_symbol = "[OK]" if result.is_healthy() else "[FAIL]"
        rating = get_response_time_rating(result.response_time_ms)
        
        summary_lines.append(f"{status_symbol} {result.service.upper()}: {result.status} ({result.response_time_ms:.1f}ms, {rating})")
        
        if result.error:
            summary_lines.append(f"    ERROR: {result.error}")
        
        if result.details:
            summary_lines.append(f"    Details: {result.details}")
    
    return "\n".join(summary_lines)


# Export all public components
__all__ = [
    'HealthCheckResult',
    'SERVICE_ENDPOINTS', 
    'DATABASE_TIMEOUTS',
    'HEALTH_STATUS',
    'RESPONSE_TIME_THRESHOLDS',
    'get_response_time_rating',
    'create_service_error_result',
    'create_timeout_result', 
    'create_healthy_result',
    'create_disabled_result',
    'validate_service_response',
    'get_critical_services',
    'calculate_overall_health_score',
    'format_health_summary'
]