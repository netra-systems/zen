"""Unified Health Monitoring System

Standardized health checks and responses for Enterprise SLA compliance.
Prevents $10K MRR loss from downtime with 99.9% uptime monitoring.

Business Value:
- Enterprise segment SLA compliance
- Unified monitoring across all services  
- Circuit breaker integration for reliability
- Telemetry for revenue protection
"""

from .interface import BaseHealthChecker, HealthInterface, HealthLevel
from .responses import (
    HealthResponseFormat, 
    StandardHealthResponse,
    ComprehensiveHealthResponse,
    HealthResponseBuilder
)
from .checks import (
    DatabaseHealthChecker,
    ServiceHealthChecker,
    DependencyHealthChecker,
    CircuitBreakerHealthChecker
)
from .telemetry import (
    EnterpriseHealthTelemetry,
    TelemetryManager,
    telemetry_manager
)

__all__ = [
    "BaseHealthChecker",
    "HealthInterface",
    "HealthLevel",
    "HealthResponseFormat",
    "StandardHealthResponse",
    "ComprehensiveHealthResponse", 
    "HealthResponseBuilder",
    "DatabaseHealthChecker",
    "ServiceHealthChecker", 
    "DependencyHealthChecker",
    "CircuitBreakerHealthChecker",
    "EnterpriseHealthTelemetry",
    "TelemetryManager",
    "telemetry_manager"
]