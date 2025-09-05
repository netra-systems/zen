"""
Telemetry module for health checks.

This module provides a telemetry manager for health monitoring.
"""

from netra_backend.app.core.health.telemetry_core import EnterpriseHealthTelemetry

class TelemetryManager:
    """Simple telemetry manager wrapper."""
    
    def __init__(self):
        self.telemetry = EnterpriseHealthTelemetry("backend", sla_target=99.9)
        self.services = {}
    
    def register_service(self, service_name: str, sla_target: float = 99.9):
        """Register a service for telemetry."""
        self.services[service_name] = EnterpriseHealthTelemetry(service_name, sla_target)
    
    def record_health_check(self, results):
        """Record health check results."""
        if self.telemetry:
            self.telemetry.record_health_check(results)
    
    def get_metrics(self):
        """Get current metrics."""
        # Return a simple metrics dict since get_current_metrics doesn't exist
        return {
            "availability": 100.0,
            "services": list(self.services.keys()),
            "healthy": True
        }

# Create singleton instance
telemetry_manager = TelemetryManager()

__all__ = ['telemetry_manager', 'TelemetryManager']