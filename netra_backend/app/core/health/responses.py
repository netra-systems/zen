"""Standardized Health Response Formats

Unified response schemas for Enterprise SLA monitoring and compliance.
Ensures consistent health data across all Netra services.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class HealthResponseFormat(Enum):
    """Supported health response formats."""
    BASIC = "basic"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    ENTERPRISE = "enterprise"


class StandardHealthResponse(BaseModel):
    """Standard health response for all services."""
    status: str = Field(..., description="Health status: healthy, degraded, unhealthy, critical")
    service: str = Field(..., description="Service name identifier")
    version: str = Field(default="1.0.0", description="Service version")
    timestamp: str = Field(..., description="ISO timestamp of health check")
    uptime_seconds: Optional[float] = Field(None, description="Service uptime in seconds")
    environment: Optional[str] = Field(None, description="Deployment environment")


class ComponentCheckResult(BaseModel):
    """Individual component health check result."""
    success: bool = Field(..., description="Whether check passed")
    health_score: float = Field(..., ge=0.0, le=1.0, description="Health score 0.0-1.0")
    response_time_ms: float = Field(..., description="Check response time in milliseconds")
    error: Optional[str] = Field(None, description="Error message if check failed")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class ComprehensiveHealthResponse(StandardHealthResponse):
    """Comprehensive health response with detailed metrics."""
    checks: Dict[str, ComponentCheckResult] = Field(default_factory=dict)
    metrics: Dict[str, Any] = Field(default_factory=dict)
    alerts: Optional[List[Dict[str, Any]]] = Field(default_factory=list)
    sla_status: Optional[Dict[str, Any]] = Field(None, description="SLA compliance status")


class EnterpriseHealthResponse(ComprehensiveHealthResponse):
    """Enterprise-grade health response with SLA monitoring."""
    availability_percentage: float = Field(..., description="Current availability percentage")
    sla_target: float = Field(default=99.9, description="Target SLA percentage")
    incident_count_24h: int = Field(default=0, description="Incidents in last 24 hours")
    recovery_time_avg_ms: float = Field(..., description="Average recovery time")
    telemetry: Dict[str, Any] = Field(default_factory=dict)


class HealthResponseBuilder:
    """Builder for creating standardized health responses."""
    
    def __init__(self, service_name: str, version: str = "1.0.0"):
        self.service_name = service_name
        self.version = version
        self.environment = self._detect_environment()
    
    def create_basic_response(self, status: str = "healthy") -> Dict[str, Any]:
        """Create basic health response."""
        return {
            "status": status,
            "service": self.service_name,
            "version": self.version,
            "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
            "environment": self.environment
        }
    
    def create_standard_response(
        self, 
        status: str,
        uptime_seconds: float,
        checks: Optional[Dict[str, bool]] = None
    ) -> Dict[str, Any]:
        """Create standard health response with basic checks."""
        response = self.create_basic_response(status)
        response.update({
            "uptime_seconds": uptime_seconds,
            "checks": checks or {}
        })
        return response
    
    def create_comprehensive_response(
        self,
        status: str,
        uptime_seconds: float,
        detailed_checks: Dict[str, ComponentCheckResult],
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create comprehensive health response."""
        response = self.create_standard_response(status, uptime_seconds)
        response.update({
            "checks": {name: check.model_dump() for name, check in detailed_checks.items()},
            "metrics": metrics,
            "sla_status": self._calculate_sla_status(detailed_checks)
        })
        return response
    
    def create_enterprise_response(
        self,
        status: str,
        uptime_seconds: float,
        detailed_checks: Dict[str, ComponentCheckResult],
        metrics: Dict[str, Any],
        availability_percentage: float
    ) -> Dict[str, Any]:
        """Create enterprise health response with SLA monitoring."""
        response = self.create_comprehensive_response(
            status, uptime_seconds, detailed_checks, metrics
        )
        response.update({
            "availability_percentage": availability_percentage,
            "sla_target": 99.9,
            "incident_count_24h": metrics.get("incident_count_24h", 0),
            "recovery_time_avg_ms": metrics.get("recovery_time_avg_ms", 0),
            "telemetry": self._build_telemetry_data(metrics)
        })
        return response
    
    def _detect_environment(self) -> str:
        """Detect current deployment environment."""
        from netra_backend.app.core.configuration import unified_config_manager
        config = unified_config_manager.get_config()
        return config.environment
    
    def _calculate_sla_status(self, checks: Dict[str, ComponentCheckResult]) -> Dict[str, Any]:
        """Calculate SLA compliance status from check results."""
        if not checks:
            return {"compliant": True, "target": 99.9, "current": 100.0}
        
        successful_checks = sum(1 for check in checks.values() if check.success)
        total_checks = len(checks)
        current_availability = (successful_checks / total_checks) * 100
        
        return {
            "compliant": current_availability >= 99.9,
            "target": 99.9,
            "current": current_availability,
            "failed_components": [
                name for name, check in checks.items() if not check.success
            ]
        }
    
    def _build_telemetry_data(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Build telemetry data for Enterprise monitoring."""
        return {
            "monitoring_enabled": True,
            "circuit_breaker_active": metrics.get("circuit_breaker_enabled", False),
            "auto_recovery_enabled": True,
            "alerting_configured": True
        }