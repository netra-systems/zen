"""Enterprise Health Telemetry and Metrics Collection

Revenue-protecting telemetry for Enterprise SLA monitoring and compliance.
Prevents $10K MRR loss through proactive health monitoring and alerting.
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, UTC, timedelta
from dataclasses import dataclass, field
from enum import Enum

from app.logging_config import central_logger
from ..health_types import HealthCheckResult, HealthStatus

logger = central_logger.get_logger(__name__)


class MetricType(Enum):
    """Types of health metrics for Enterprise monitoring."""
    AVAILABILITY = "availability"
    RESPONSE_TIME = "response_time"
    ERROR_RATE = "error_rate"
    SLA_COMPLIANCE = "sla_compliance"
    INCIDENT_COUNT = "incident_count"
    RECOVERY_TIME = "recovery_time"


@dataclass
class HealthMetric:
    """Individual health metric data point."""
    metric_type: MetricType
    value: float
    timestamp: datetime
    service_name: str
    component_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SLAViolation:
    """SLA violation event for Enterprise monitoring."""
    violation_id: str
    service_name: str
    component_name: str
    violation_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    impact_severity: str = "medium"
    resolved: bool = False


class EnterpriseHealthTelemetry:
    """Enterprise-grade health telemetry collector."""
    
    def __init__(self, service_name: str, sla_target: float = 99.9):
        self.service_name = service_name
        self.sla_target = sla_target
        self._metrics: List[HealthMetric] = []
        self._violations: List[SLAViolation] = []
        self._current_availability = 100.0
        self._last_health_check = datetime.now(UTC)
    
    def record_health_check(self, results: Dict[str, HealthCheckResult]) -> None:
        """Record health check results for telemetry analysis."""
        timestamp = datetime.now(UTC)
        
        # Calculate availability metrics
        availability = self._calculate_availability(results)
        self._record_metric(MetricType.AVAILABILITY, availability, timestamp)
        
        # Record component-specific metrics
        for component_name, result in results.items():
            self._record_component_metrics(component_name, result, timestamp)
        
        # Check for SLA violations
        self._check_sla_compliance(availability, timestamp)
        
        self._last_health_check = timestamp
    
    def _calculate_availability(self, results: Dict[str, HealthCheckResult]) -> float:
        """Calculate current availability percentage."""
        if not results:
            return 100.0
        
        successful_checks = sum(1 for result in results.values() if result.success)
        return (successful_checks / len(results)) * 100.0
    
    def _record_component_metrics(
        self, 
        component_name: str, 
        result: HealthCheckResult, 
        timestamp: datetime
    ) -> None:
        """Record metrics for individual component."""
        # Response time metric
        self._record_metric(
            MetricType.RESPONSE_TIME, 
            result.response_time_ms, 
            timestamp, 
            component_name
        )
        
        # Error rate metric (1.0 for failure, 0.0 for success)
        error_rate = 0.0 if result.success else 1.0
        self._record_metric(
            MetricType.ERROR_RATE, 
            error_rate, 
            timestamp, 
            component_name
        )
    
    def _record_metric(
        self, 
        metric_type: MetricType, 
        value: float, 
        timestamp: datetime, 
        component_name: Optional[str] = None
    ) -> None:
        """Record a health metric."""
        metric = HealthMetric(
            metric_type=metric_type,
            value=value,
            timestamp=timestamp,
            service_name=self.service_name,
            component_name=component_name
        )
        self._metrics.append(metric)
        
        # Keep only last 24 hours of metrics
        self._cleanup_old_metrics()
    
    def _check_sla_compliance(self, availability: float, timestamp: datetime) -> None:
        """Check for SLA violations and record if necessary."""
        if availability < self.sla_target:
            self._record_sla_violation(availability, timestamp)
        else:
            self._resolve_active_violations(timestamp)
    
    def _record_sla_violation(self, availability: float, timestamp: datetime) -> None:
        """Record an SLA violation event."""
        # Check if we already have an active violation
        active_violations = [v for v in self._violations if not v.resolved]
        
        if not active_violations:
            violation = SLAViolation(
                violation_id=f"{self.service_name}_{int(timestamp.timestamp())}",
                service_name=self.service_name,
                component_name="system",
                violation_type="availability_below_sla",
                start_time=timestamp,
                impact_severity=self._determine_severity(availability)
            )
            self._violations.append(violation)
            logger.warning(f"SLA violation detected: {availability:.2f}% < {self.sla_target}%")
    
    def _resolve_active_violations(self, timestamp: datetime) -> None:
        """Resolve any active SLA violations."""
        for violation in self._violations:
            if not violation.resolved:
                violation.end_time = timestamp
                violation.resolved = True
                
                # Calculate recovery time
                if violation.start_time:
                    recovery_time = (timestamp - violation.start_time).total_seconds() * 1000
                    self._record_metric(MetricType.RECOVERY_TIME, recovery_time, timestamp)
                
                logger.info(f"SLA violation resolved: {violation.violation_id}")
    
    def _determine_severity(self, availability: float) -> str:
        """Determine severity of SLA violation."""
        if availability < 95.0:
            return "critical"
        elif availability < 98.0:
            return "high"
        elif availability < 99.5:
            return "medium"
        else:
            return "low"
    
    def _cleanup_old_metrics(self) -> None:
        """Remove metrics older than 24 hours."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=24)
        self._metrics = [m for m in self._metrics if m.timestamp > cutoff_time]
        
        # Also cleanup old violations (keep last 7 days)
        violation_cutoff = datetime.now(UTC) - timedelta(days=7)
        self._violations = [v for v in self._violations if v.start_time > violation_cutoff]
    
    def get_enterprise_metrics(self) -> Dict[str, Any]:
        """Get Enterprise-grade metrics for SLA monitoring."""
        recent_metrics = self._get_recent_metrics(hours=1)
        
        return {
            "current_availability": self._get_current_availability(),
            "sla_target": self.sla_target,
            "sla_compliant": self._is_sla_compliant(),
            "incidents_24h": self._count_recent_incidents(hours=24),
            "average_response_time_ms": self._get_average_response_time(recent_metrics),
            "error_rate_percentage": self._get_error_rate(recent_metrics),
            "active_violations": len([v for v in self._violations if not v.resolved]),
            "last_health_check": self._last_health_check.isoformat(),
            "telemetry_enabled": True
        }
    
    def _get_recent_metrics(self, hours: int) -> List[HealthMetric]:
        """Get metrics from the last N hours."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        return [m for m in self._metrics if m.timestamp > cutoff_time]
    
    def _get_current_availability(self) -> float:
        """Get current availability percentage."""
        recent_availability = [
            m for m in self._get_recent_metrics(hours=1) 
            if m.metric_type == MetricType.AVAILABILITY
        ]
        
        if not recent_availability:
            return 100.0
        
        return recent_availability[-1].value
    
    def _is_sla_compliant(self) -> bool:
        """Check if currently SLA compliant."""
        return self._get_current_availability() >= self.sla_target
    
    def _count_recent_incidents(self, hours: int) -> int:
        """Count incidents in the last N hours."""
        cutoff_time = datetime.now(UTC) - timedelta(hours=hours)
        return len([v for v in self._violations if v.start_time > cutoff_time])
    
    def _get_average_response_time(self, metrics: List[HealthMetric]) -> float:
        """Calculate average response time from metrics."""
        response_times = [
            m.value for m in metrics 
            if m.metric_type == MetricType.RESPONSE_TIME
        ]
        
        if not response_times:
            return 0.0
        
        return sum(response_times) / len(response_times)
    
    def _get_error_rate(self, metrics: List[HealthMetric]) -> float:
        """Calculate error rate percentage from metrics."""
        error_metrics = [
            m for m in metrics 
            if m.metric_type == MetricType.ERROR_RATE
        ]
        
        if not error_metrics:
            return 0.0
        
        total_errors = sum(m.value for m in error_metrics)
        return (total_errors / len(error_metrics)) * 100.0


class TelemetryManager:
    """Global telemetry manager for Enterprise health monitoring."""
    
    def __init__(self):
        self._service_telemetry: Dict[str, EnterpriseHealthTelemetry] = {}
    
    def register_service(self, service_name: str, sla_target: float = 99.9) -> None:
        """Register a service for telemetry monitoring."""
        self._service_telemetry[service_name] = EnterpriseHealthTelemetry(
            service_name, sla_target
        )
        logger.info(f"Registered telemetry for service: {service_name}")
    
    def record_health_data(
        self, 
        service_name: str, 
        health_results: Dict[str, HealthCheckResult]
    ) -> None:
        """Record health data for a service."""
        if service_name in self._service_telemetry:
            self._service_telemetry[service_name].record_health_check(health_results)
    
    def get_service_metrics(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Get Enterprise metrics for a specific service."""
        if service_name in self._service_telemetry:
            return self._service_telemetry[service_name].get_enterprise_metrics()
        return None
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get Enterprise metrics for all monitored services."""
        return {
            service_name: telemetry.get_enterprise_metrics()
            for service_name, telemetry in self._service_telemetry.items()
        }


# Global telemetry manager instance
telemetry_manager = TelemetryManager()