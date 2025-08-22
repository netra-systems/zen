"""Unified Health Monitoring System

Standardized health checks and responses for Enterprise SLA compliance.
Prevents $10K MRR loss from downtime with 99.9% uptime monitoring.

Business Value:
- Enterprise segment SLA compliance
- Unified monitoring across all services  
- Circuit breaker integration for reliability
- Telemetry for revenue protection
"""

from netra_backend.app.core.health.checks import (
    CircuitBreakerHealthChecker,
    DatabaseHealthChecker,
    DependencyHealthChecker,
    ServiceHealthChecker,
)
from netra_backend.app.core.health.interface import (
    BaseHealthChecker,
    HealthInterface,
    HealthLevel,
)
from netra_backend.app.core.health.responses import (
    ComprehensiveHealthResponse,
    HealthResponseBuilder,
    HealthResponseFormat,
    StandardHealthResponse,
)
from netra_backend.app.core.health.telemetry import (
    EnterpriseHealthTelemetry,
    TelemetryManager,
    telemetry_manager,
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