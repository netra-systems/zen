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

from datetime import UTC, datetime
from typing import Any, Dict, Optional
from enum import Enum
from dataclasses import dataclass

# Set testing environment before any imports
from shared.isolated_environment import get_env
env = get_env()
env.set("TESTING", "1", "test")
env.set("ENVIRONMENT", "testing", "test")
env.set("DATABASE_URL", "sqlite+aiosqlite:///:memory:", "test")


@dataclass
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
        return f"HealthCheckResult(service={self.service}, status={self.status}, response_time={self.response_time_ms}ms)"


# Service endpoints and timeout configurations
SERVICE_ENDPOINTS = {
    "auth": {
        "urls": [
            "http://localhost:8081/health",
            "http://localhost:8083/health",  # Alternative port
            "http://127.0.0.1:8081/health"
        ],
        "timeout": 10.0,
        "expected_service": "auth-service",
        "critical": True,
        "fallback_ports": [8081, 8083]
    },
    "backend": {
        "urls": [
            "http://localhost:8000/health",
            "http://localhost:8000/health/",  # Alternative endpoint format
            "http://localhost:8200/health",   # Alternative port
            "http://127.0.0.1:8000/health"
        ],
        "timeout": 10.0,
        "expected_service": ["netra_backend", "netra-ai-platform"],  # Allow both service names
        "critical": True,
        "fallback_ports": [8000, 8200]
    },
    "frontend": {
        "urls": [
            "http://localhost:3000",
            "http://localhost:3000/",
            "http://127.0.0.1:3000"
        ],
        "timeout": 15.0,
        "check_type": "build_verification",
        "critical": False,
        "fallback_ports": [3000, 3001]
    }
}

# Database timeout configurations
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


def validate_service_response(response_data: Dict[str, Any], expected_service) -> bool:
    """Validate service response matches expected service identifier."""
    if not expected_service:
        return True

    actual_service = response_data.get("service")

    # Handle both single service name and list of acceptable service names
    if isinstance(expected_service, list):
        return actual_service in expected_service
    else:
        return actual_service == expected_service


def get_critical_services() -> list[str]:
    """Get list of services marked as critical for system operation."""
    return [
        service_name for service_name, config in SERVICE_ENDPOINTS.items()
        if config.get("critical", False)
    ]


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
        f"System Health Score: {health_score:.2f} ({healthy_count}/{total_count} services healthy)",
        f"Overall Status: {'HEALTHY' if health_score > 0.8 else 'DEGRADED' if health_score > 0.5 else 'CRITICAL'}",
        ""
    ]

    for result in results:
        status_symbol = "[OK]" if result.is_healthy() else "[FAIL]"
        rating = get_response_time_rating(result.response_time_ms)

        summary_lines.append(f"{status_symbol} {result.service}: {result.status} ({rating}, {result.response_time_ms:.1f}ms)")

        if result.error:
            summary_lines.append(f"    Error: {result.error}")

        if result.details:
            summary_lines.append(f"    Details: {result.details}")

    return "\n".join(summary_lines)


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class HealthChecker:
    """
    Health Checker - Performs health checks on services
    
    PLACEHOLDER IMPLEMENTATION - Provides minimal interface for test collection.
    """
    
    def __init__(self):
        """Initialize health checker"""
        self.service_endpoints = SERVICE_ENDPOINTS
    
    async def check_service_health(self, service_name: str) -> HealthCheckResult:
        """
        Check health of specific service
        
        Args:
            service_name: Name of service to check
            
        Returns:
            HealthCheckResult with health status
        """
        # PLACEHOLDER IMPLEMENTATION
        return HealthCheckResult(
            service=service_name,
            status=HEALTH_STATUS["HEALTHY"],
            response_time_ms=1.0,
            details={'placeholder': True}
        )


# Export all public components
__all__ = [
    'HealthCheckResult',
    'HealthChecker',
    'HealthStatus',
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