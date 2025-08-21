"""Health Telemetry Data Types

Revenue-protecting telemetry types for Enterprise SLA monitoring and compliance.
Prevents $10K MRR loss through proactive health monitoring and alerting.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


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