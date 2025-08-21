"""Alert data models and enums for the monitoring system.

Defines core alert types, severity levels, and data structures
used throughout the alert management system.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AlertLevel(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning" 
    ERROR = "error"
    CRITICAL = "critical"


class NotificationChannel(Enum):
    """Available notification channels."""
    LOG = "log"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    DATABASE = "database"


@dataclass
class AlertRule:
    """Configuration for an alert rule."""
    rule_id: str
    name: str
    description: str
    condition: str  # Python expression string
    level: AlertLevel
    threshold_value: float
    time_window_minutes: int = 5
    evaluation_interval_seconds: int = 30
    cooldown_minutes: int = 15
    channels: List[NotificationChannel] = field(default_factory=list)
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Alert:
    """Alert instance."""
    alert_id: str
    rule_id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    agent_name: Optional[str] = None
    metric_name: Optional[str] = None
    current_value: Optional[float] = None
    threshold_value: Optional[float] = None
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    suppressed: bool = False
    suppression_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class NotificationConfig:
    """Configuration for notification channels."""
    channel: NotificationChannel
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    rate_limit_per_hour: int = 100
    min_level: AlertLevel = AlertLevel.INFO