"""Quality Monitoring Service - Compatibility wrapper

This module provides backward compatibility for the refactored quality monitoring service.
The actual implementation is now modularized in the quality_monitoring package.
"""

from netra_backend.app.services.quality_monitoring import (
    QualityMonitoringService,
    AlertSeverity,
    MetricType,
    QualityAlert,
    QualityTrend,
    AgentQualityProfile
)

__all__ = [
    'QualityMonitoringService',
    'AlertSeverity',
    'MetricType',
    'QualityAlert',
    'QualityTrend',
    'AgentQualityProfile'
]