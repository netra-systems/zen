"""Telemetry Manager for Enterprise Health Monitoring

Revenue-protecting telemetry manager for Enterprise SLA monitoring and compliance.
Prevents $10K MRR loss through proactive health monitoring and alerting.
"""

from typing import Dict, Any, Optional

from netra_backend.app.logging_config import central_logger
from netra_backend.app..health_types import HealthCheckResult
from netra_backend.app.telemetry_core import EnterpriseHealthTelemetry

logger = central_logger.get_logger(__name__)


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